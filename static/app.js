let currentStatus = null;
let statusPollInterval = null;
let wasConnected = false;

document.addEventListener('DOMContentLoaded', () => {
    initUI();
    startStatusPolling();
    checkForUpdates();
});

let isRefreshing = false;

// 창을 닫을 때(beforeunload) 즉시 서버에 셧다운 요청 전송
// (단, 의도적인 새로고침일 때는 전송하지 않음)
window.addEventListener('beforeunload', () => {
    if (!isRefreshing) {
        navigator.sendBeacon('/api/shutdown');
    }
});

function initUI() {
    // Buttons
    document.getElementById('btn-open-device').addEventListener('click', handleOpenDevice);
    document.getElementById('btn-start-scan').addEventListener('click', handleStartScan);
    document.getElementById('btn-cancel-scan').addEventListener('click', handleCancelScan);
    document.getElementById('btn-execute-fetch').addEventListener('click', handleExecuteFetch);
    document.getElementById('btn-open-save-folder').addEventListener('click', handleOpenSaveDir);
    document.getElementById('btn-back-home').addEventListener('click', () => {
        const inputTag = document.getElementById('input-tag');
        if (inputTag) inputTag.dataset.loaded = 'false';
        switchView('view-home');
    });

    // Modal Settings
    document.getElementById('btn-open-settings').addEventListener('click', openSettingsModal);
    document.getElementById('btn-close-modal').addEventListener('click', closeSettingsModal);
    document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
    document.getElementById('btn-cancel-settings').addEventListener('click', closeSettingsModal);
    
    // Delete Confirmation
    document.getElementById('btn-delete-yes').addEventListener('click', () => {
        // 일괄삭제한다는 안내 표시
        const modal = document.getElementById('modal-delete-confirm');
        modal.innerHTML = '<div class="modal-card"><p>일괄 삭제를 시작합니다...</p></div>';
        
        // 약간의 딜레이 후 삭제 요청 (사용자가 텍스트를 볼 수 있도록)
        setTimeout(() => {
            modal.classList.add('hidden');
            fetch('/api/fetch/delete-originals', { method: 'POST' });
        }, 1000);
    });

    document.getElementById('btn-delete-no').addEventListener('click', () => {
        document.getElementById('modal-delete-confirm').classList.add('hidden');
        appCloseFlow("원본 파일을 삭제하지 않습니다. 앱을 곧 종료합니다.");
    });
    
    // AutoRun Setup Buttons
    document.getElementById('btn-autorun-register').addEventListener('click', handleAutorunRegister);
    document.getElementById('btn-autorun-unregister').addEventListener('click', handleAutorunUnregister);
    
    // Directory Picker
    document.getElementById('btn-select-dir').addEventListener('click', handleSelectDir);

    // Camera Registration
    document.getElementById('btn-register-camera').addEventListener('click', handleRegisterCurrentCamera);

    // Update
    const btnUpdate = document.getElementById('btn-do-update');
    if (btnUpdate) {
        btnUpdate.addEventListener('click', handleDoUpdate);
    }
}

let latestUpdateData = null;

function checkForUpdates() {
    fetch('/api/check-update')
        .then(res => res.json())
        .then(data => {
            const banner = document.getElementById('update-banner');
            const title = document.getElementById('update-banner-title');
            const versionText = document.getElementById('update-version-text');
            const btnUpdate = document.getElementById('btn-do-update');
            
            // 데이터가 없거나 에러가 있으면 배너 숨김
            if (data.error || !data.current_version) {
                return;
            }

            banner.classList.remove('hidden');

            if (data.has_update && data.assets && data.assets.length > 0) {
                latestUpdateData = data;
                title.innerText = "🎉 새 버전 업데이트 가능!";
                versionText.innerText = data.current_version + " ➔ " + data.latest_version;
                btnUpdate.classList.remove('hidden');
                
                banner.style.backgroundColor = "#d1ecf1";
                banner.style.color = "#0c5460";
                banner.style.borderBottom = "1px solid #bee5eb";
            } else {
                title.innerText = "✅ 최신 버전을 사용 중입니다.";
                versionText.innerText = data.current_version;
                btnUpdate.classList.add('hidden');
                
                banner.style.backgroundColor = "#e8f5e9";
                banner.style.color = "#2e7d32";
                banner.style.borderBottom = "1px solid #c8e6c9";
            }
        })
        .catch(err => console.error("Update check failed:", err));
}

let updatePollInterval = null;

function handleDoUpdate() {
    if (!latestUpdateData || !latestUpdateData.assets || latestUpdateData.assets.length === 0) return;
    
    const zipAsset = latestUpdateData.assets.find(a => a.name.endsWith('.zip'));
    if (!zipAsset) {
        alert("업데이트 압축 파일(.zip)을 찾을 수 없습니다.");
        return;
    }

    // Hide banner, show progress modal
    document.getElementById('update-banner').classList.add('hidden');
    document.getElementById('modal-update-progress').classList.remove('hidden');

    fetch('/api/download-update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: zipAsset.browser_download_url })
    }).then(res => res.json()).then(data => {
        if (data.success) {
            updatePollInterval = setInterval(pollUpdateProgress, 500);
        } else {
            alert("다운로드 시작 실패: " + data.error);
            document.getElementById('modal-update-progress').classList.add('hidden');
        }
    }).catch(err => {
        alert("다운로드 요청 오류");
        document.getElementById('modal-update-progress').classList.add('hidden');
    });
}

function pollUpdateProgress() {
    fetch('/api/download-progress')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'downloading' || data.status === 'completed') {
                document.getElementById('update-progress-fill').style.width = data.percent + '%';
                document.getElementById('update-progress-pct').innerText = data.percent + '%';
                
                if (data.status === 'completed') {
                    clearInterval(updatePollInterval);
                    document.getElementById('update-status-text').innerText = "다운로드 완료! 업데이트를 적용합니다...";
                    setTimeout(applyUpdate, 1000);
                }
            } else if (data.status === 'error') {
                clearInterval(updatePollInterval);
                alert("업데이트 다운로드 중 오류 발생: " + data.error);
                document.getElementById('modal-update-progress').classList.add('hidden');
            }
        })
        .catch(console.error);
}

function applyUpdate() {
    fetch('/api/apply-update', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // The backend will shutdown and run update.bat
                // We'll show a closing flow and then close the browser window.
                document.getElementById('modal-update-progress').classList.add('hidden');
                appCloseFlow("업데이트 적용을 위해 앱이 재시작됩니다.");
            } else {
                alert("업데이트 적용 실패: " + data.error);
                document.getElementById('modal-update-progress').classList.add('hidden');
            }
        });
}

function startStatusPolling() {
    fetchStatus();
}

function fetchStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            if (wasConnected && !data.connected) {
                handleDisconnectShutdown();
            }
            wasConnected = data.connected;

            currentStatus = data;
            updateMainStatusView(data);
            updateProcessView(data);
            
            // Adjust polling rate: extremely fast during scanning/fetching to see fast file changes
            let isBusy = (data.scan && data.scan.status === 'scanning') || 
                         (data.fetch && data.fetch.status === 'fetching') ||
                         (data.delete && data.delete.status === 'deleting');
                         
            // 자동 가져오기가 백그라운드에서 돌고 있다면 화면을 자동으로 "가져오기 진행" 탭으로 전환
            if (isBusy) {
                const processView = document.getElementById('view-process');
                if (processView && processView.classList.contains('hidden')) {
                    switchView('view-process');
                }
            }
            
            setTimeout(fetchStatus, isBusy ? 50 : 1500);
        })
        .catch(err => {
            console.error("Error fetching status:", err);
            setTimeout(fetchStatus, 1500);
        });
}

function handleDisconnectShutdown() {
    if (window.isShuttingDown) return;
    window.isShuttingDown = true;

    // Show disconnect modal
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.zIndex = '9999';
    overlay.innerHTML = `
        <div class="modal-card" style="text-align:center;">
            <h2>🔌 카메라 연결 끊김</h2>
            <p>USB 연결이 해제되었습니다.</p>
            <p><strong id="shutdown-timer" style="font-size: 1.5em; color: #e74c3c;">3</strong>초 후 프로그램이 종료됩니다.</p>
        </div>
    `;
    document.body.appendChild(overlay);

    let count = 3;
    const timerEl = document.getElementById('shutdown-timer');
    const interval = setInterval(() => {
        count--;
        if (timerEl) timerEl.innerText = count;
        if (count <= 0) {
            clearInterval(interval);
            fetch('/api/shutdown', { method: 'POST' }).then(() => {
                window.close(); // Try to close the browser tab/window
            }).catch(() => window.close());
        }
    }, 1000);
}

function appCloseFlow(message) {
    if (window.isShuttingDown) return;
    window.isShuttingDown = true;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.zIndex = '9999';
    overlay.innerHTML = `
        <div class="modal-card" style="text-align:center;">
            <h2>안내</h2>
            <p>${message}</p>
            <p><strong id="closing-timer" style="font-size: 1.5em; color: #e74c3c;">3</strong>초 후 프로그램이 종료됩니다.</p>
        </div>
    `;
    document.body.appendChild(overlay);

    let count = 3;
    const timerEl = document.getElementById('closing-timer');
    const interval = setInterval(() => {
        count--;
        if (timerEl) timerEl.innerText = count;
        if (count <= 0) {
            clearInterval(interval);
            fetch('/api/shutdown', { method: 'POST' }).then(() => {
                window.close();
            }).catch(() => window.close());
        }
    }, 1000);
}

function updateMainStatusView(data) {
    const statusCard = document.getElementById('status-card');
    const statusText = document.getElementById('status-text');
    const modelText = document.getElementById('model-text');
    const actionGrid = document.getElementById('action-group');

    if (data.connected) {
        if (statusCard.className !== 'status-card connected') {
            statusCard.className = 'status-card connected';
        }
        safeSetText(statusText, 'DSLR 디지털 카메라 연결됨!');
        
        let fileText = '';
        if (data.scan && data.scan.status === 'scanning') {
            fileText = ` (스캔 중... ${data.scan.count}개 발견)`;
        } else if (data.scan && data.scan.status === 'complete') {
            fileText = ` - 총 ${data.scan.count}개의 미디어 파일`;
        }
        
        safeSetText(modelText, '감지된 모델: ' + (data.model || 'PTP Camera') + fileText);
        if (actionGrid.classList.contains('disabled')) {
            actionGrid.classList.remove('disabled');
        }
    } else {
        if (statusCard.className !== 'status-card disconnected') {
            statusCard.className = 'status-card disconnected';
        }
        safeSetText(statusText, 'DSLR 디지털 카메라 연결 대기 중...');
        safeSetText(modelText, 'PTP/MTP DSLR 디지털 카메라(예: Nikon D90)를 USB 포트에 연결해주세요.');
        if (!actionGrid.classList.contains('disabled')) {
            actionGrid.classList.add('disabled');
        }
    }
}

function safeSetText(elem, text) {
    if (elem && elem.innerText !== text) {
        elem.innerText = text;
    }
}

function updateProcessView(data) {
    const scan = data.scan || {};
    const fetchState = data.fetch || {};
    const deleteState = data.delete;
    const config = data.config || {};

    const processTitle = document.getElementById('process-title');
    const processSub = document.getElementById('process-sub');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressCounter = document.getElementById('progress-counter');
    const progressFile = document.getElementById('progress-file');

    const tagContainer = document.getElementById('tag-option-container');
    const btnCancelScan = document.getElementById('btn-cancel-scan');
    const btnExecuteFetch = document.getElementById('btn-execute-fetch');
    const btnOpenSaveFolder = document.getElementById('btn-open-save-folder');
    const btnBackHome = document.getElementById('btn-back-home');

    // Scanning phase
    if (scan.status === 'scanning') {
        safeSetText(processTitle, '미디어 파일 스캔 중...');
        safeSetText(processSub, 'DSLR 디지털 카메라 저장소에서 사진과 비디오를 탐색하고 있습니다.');
        
        // Use (count % 20) to show fake progress since total is unknown
        let progressPct = (scan.count % 20) * 5; 
        
        safeSetText(progressCounter, `사진 및 비디오를 ${scan.count}개 찾음`);
        safeSetText(progressFile, `검색 중: ${scan.current_file}`);
        
        // Remove transition so it doesn't animate backwards when wrapping from 95% to 0%
        progressBarFill.style.transition = 'none';
        progressBarFill.style.width = `${progressPct}%`;

        tagContainer.classList.add('hidden');
        btnCancelScan.classList.remove('hidden');
        btnExecuteFetch.classList.add('hidden');
        btnOpenSaveFolder.classList.add('hidden');
        btnBackHome.classList.add('hidden');
        
        window.deleteCompleteHandled = false;
    }
    // Scan complete phase
    else if (scan.status === 'complete' && fetchState.status === 'idle') {
        safeSetText(processTitle, '스캔 완료');
        safeSetText(processSub, `총 ${scan.count}개의 미디어 파일을 찾았습니다.`);
        safeSetText(progressCounter, `사진 및 비디오 총 ${scan.count}개 발견`);
        safeSetText(progressFile, scan.count === 0 ? '※ 기기에 사진/비디오 파일 없음' : '가져오기 준비 완료');
        
        progressBarFill.style.transition = 'width 0.3s ease';
        progressBarFill.style.width = '100%';

        btnCancelScan.classList.add('hidden');
        btnOpenSaveFolder.classList.add('hidden');
        btnBackHome.classList.remove('hidden');

        if (scan.count > 0) {
            btnExecuteFetch.classList.remove('hidden');
            if (config.chkbox_tag) {
                tagContainer.classList.remove('hidden');
                populateTagDatalist(config.taglist || []);
                const inputTag = document.getElementById('input-tag');
                if (inputTag && inputTag.dataset.loaded !== 'true') {
                    inputTag.value = '';
                    inputTag.dataset.loaded = 'true';
                }
            } else {
                tagContainer.classList.add('hidden');
            }
        } else {
            btnExecuteFetch.classList.add('hidden');
            tagContainer.classList.add('hidden');
        }
    }
    // Fetching phase
    else if (fetchState.status === 'fetching') {
        safeSetText(processTitle, '사진 및 비디오 가져오는 중...');
        safeSetText(processSub, '미디어 파일을 내 PC로 복사하고 있습니다.');
        
        progressBarFill.style.transition = 'width 0.3s ease';
        const pct = fetchState.total > 0 ? Math.round((fetchState.copied / fetchState.total) * 100) : 0;
        progressBarFill.style.width = `${pct}%`;
        safeSetText(progressCounter, `복사 진행률: ${fetchState.copied} / ${fetchState.total} (${pct}%)`);
        safeSetText(progressFile, `복사 중: ${fetchState.current_file}`);

        tagContainer.classList.add('hidden');
        btnCancelScan.classList.add('hidden');
        btnExecuteFetch.classList.add('hidden');
        btnOpenSaveFolder.classList.add('hidden');
        btnBackHome.classList.add('hidden');
    }
    // Fetch complete phase (before delete)
    else if (fetchState.status === 'complete' || fetchState.status === 'failed') {
        if (deleteState && deleteState.status === 'deleting') {
            safeSetText(processTitle, '원본 삭제 중...');
            safeSetText(processSub, '카메라에서 원본 파일을 삭제하고 있습니다.');
            
            progressBarFill.style.transition = 'width 0.3s ease';
            const pct = deleteState.total > 0 ? Math.round((deleteState.deleted / deleteState.total) * 100) : 0;
            progressBarFill.style.width = `${pct}%`;
            safeSetText(progressCounter, `삭제 진행률: ${deleteState.deleted} / ${deleteState.total} (${pct}%)`);
            safeSetText(progressFile, `삭제 중: ${deleteState.current_file}`);

            tagContainer.classList.add('hidden');
            btnCancelScan.classList.add('hidden');
            btnExecuteFetch.classList.add('hidden');
            btnOpenSaveFolder.classList.add('hidden');
            btnBackHome.classList.add('hidden');
        } else if (deleteState && (deleteState.status === 'complete' || deleteState.status === 'failed')) {
            safeSetText(processTitle, deleteState.status === 'complete' ? '삭제 완료!' : '삭제 실패');
            safeSetText(processSub, deleteState.status === 'complete' ? '선택된 원본 파일이 삭제되었습니다.' : '삭제 중 오류가 발생했습니다.');
            progressBarFill.style.width = '100%';
            safeSetText(progressCounter, `삭제된 파일: ${deleteState.deleted}개`);
            safeSetText(progressFile, '');

            tagContainer.classList.add('hidden');
            btnCancelScan.classList.add('hidden');
            btnExecuteFetch.classList.add('hidden');
            btnOpenSaveFolder.classList.remove('hidden');
            btnBackHome.classList.remove('hidden');
            
            if (deleteState.status === 'complete' && !window.deleteCompleteHandled) {
                window.deleteCompleteHandled = true;
                setTimeout(() => appCloseFlow("삭제가 정상적으로 완료되었습니다. 앱을 곧 종료합니다."), 500);
            }
        } else {
            safeSetText(processTitle, fetchState.status === 'complete' ? '가져오기 완료!' : '가져오기 실패');
            safeSetText(processSub, fetchState.status === 'complete' ? 
                '모든 미디어 파일이 내 PC에 안전하게 복사되었습니다.' : 
                '오류가 발생하여 복사를 완료하지 못했습니다.');
            
            progressBarFill.style.transition = 'width 0.3s ease';
            progressBarFill.style.width = '100%';
            safeSetText(progressCounter, `가져오기 완료 (${fetchState.copied}개 저장됨)`);
            safeSetText(progressFile, `저장 경로: ${fetchState.dest_path}`);

            tagContainer.classList.add('hidden');
            btnCancelScan.classList.add('hidden');
            btnExecuteFetch.classList.add('hidden');
            btnOpenSaveFolder.classList.remove('hidden');
            btnBackHome.classList.remove('hidden');
            
            if (fetchState.status === 'complete' && !window.hasShownDeleteConfirm) {
                window.hasShownDeleteConfirm = true;
                setTimeout(() => {
                    document.getElementById('modal-delete-confirm').classList.remove('hidden');
                }, 100);
            }
        }
    }
}

function switchView(viewId) {
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.remove('active');
        panel.classList.add('hidden');
    });

    const target = document.getElementById(viewId);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }
}

function handleOpenDevice() {
    fetch('/api/open-explorer', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert('장치 탐색기를 열지 못했습니다.');
            } else {
                window.close();
            }
        });
}

function handleStartScan() {
    window.hasShownDeleteConfirm = false;
    switchView('view-process');
    fetch('/api/scan/start', { method: 'POST' });
}

function handleCancelScan() {
    const inputTag = document.getElementById('input-tag');
    if (inputTag) inputTag.dataset.loaded = 'false';
    fetch('/api/scan/cancel', { method: 'POST' })
        .then(() => switchView('view-home'));
}

function handleExecuteFetch() {
    const inputTag = document.getElementById('input-tag');
    const tagName = inputTag ? inputTag.value.trim() : '';

    fetch('/api/fetch/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag: tagName })
    });
}

function handleOpenSaveDir() {
    const destPath = currentStatus && currentStatus.fetch ? currentStatus.fetch.dest_path : null;
    fetch('/api/open-save-dir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dest_path: destPath })
    });
}

function handleSelectDir() {
    fetch('/api/select-dir')
        .then(res => res.json())
        .then(data => {
            if (data.path) {
                document.getElementById('setting-save-dir').value = data.path;
            }
        });
}

function populateTagDatalist(tags) {
    const datalist = document.getElementById('tag-history-list');
    // Include </option> to match browser's HTML serialization, avoiding endless rewrites
    const newHTML = tags.map(t => `<option value="${t}"></option>`).join('');
    if (datalist.innerHTML !== newHTML) {
        datalist.innerHTML = newHTML;
    }
}

/* Modal Settings Functions */
let originalConfig = null;

function openSettingsModal() {
    fetch('/api/settings')
        .then(res => res.json())
        .then(cfg => {
            originalConfig = cfg;
            document.getElementById('setting-chkbox-tag').checked = cfg.chkbox_tag !== false;
            
            const chkboxAutorun = document.getElementById('setting-chkbox-autorun');
            chkboxAutorun.checked = cfg.chkbox_autorun === true;
            
            document.getElementById('setting-chkbox-explorer').checked = cfg.chkbox_explorer !== false;
            document.getElementById('setting-save-dir').value = cfg.save_dir || '';
            document.getElementById('setting-autorun-tag').value = cfg.autorun_tag || '';
            
            // Ensure datalist is populated for settings
            populateTagDatalist(cfg.taglist || []);

            // Toggle visibility of autorun tag container
            const toggleAutorunTag = () => {
                const container = document.getElementById('setting-autorun-tag-container');
                if (chkboxAutorun.checked) {
                    container.style.display = 'block';
                } else {
                    container.style.display = 'none';
                }
            };
            chkboxAutorun.removeEventListener('change', toggleAutorunTag);
            chkboxAutorun.addEventListener('change', toggleAutorunTag);
            toggleAutorunTag();

            document.getElementById('modal-settings').classList.remove('hidden');
            
            // Check AutoRun status when modal opens
            checkAutorunStatus();
            
            // Load and render registered cameras
            loadRegisteredCameras();
        });
}

function loadRegisteredCameras() {
    fetch('/api/cameras/list')
        .then(res => res.json())
        .then(data => {
            const chkboxOnlyReg = document.getElementById('setting-autorun-only-registered');
            chkboxOnlyReg.checked = data.autorun_only_registered !== false;
            
            const container = document.getElementById('camera-list-container');
            container.innerHTML = '';
            
            if (data.registered_cameras && data.registered_cameras.length > 0) {
                data.registered_cameras.forEach(cam => {
                    const item = document.createElement('div');
                    item.style.display = 'flex';
                    item.style.justifyContent = 'space-between';
                    item.style.alignItems = 'center';
                    item.style.padding = '4px 0';
                    item.style.borderBottom = '1px solid #ddd';
                    
                    item.innerHTML = `
                        <div>
                            <strong>${cam.name || cam.model}</strong><br>
                            <small style="color: #666;">SN: ${cam.serial}</small>
                        </div>
                        <button class="btn secondary" style="padding: 2px 8px; font-size: 12px; color: #e74c3c; border-color: #e74c3c;" onclick="handleDeleteCamera('${cam.serial}')">삭제</button>
                    `;
                    container.appendChild(item);
                });
            } else {
                container.innerHTML = '<div style="color: #999; font-size: 12px; text-align: center; padding: 10px;">등록된 기기가 없습니다.</div>';
            }
            
            // Show current camera box if connected
            const currentBox = document.getElementById('current-camera-box');
            if (currentStatus && currentStatus.connected && currentStatus.serial) {
                document.getElementById('current-camera-model').innerText = currentStatus.model || '알 수 없는 모델';
                document.getElementById('current-camera-serial').innerText = `SN: ${currentStatus.serial}`;
                currentBox.style.display = 'flex';
                
                // Hide register button if already registered
                const isAlreadyRegistered = data.registered_cameras.some(c => c.serial === currentStatus.serial);
                document.getElementById('btn-register-camera').style.display = isAlreadyRegistered ? 'none' : 'block';
            } else {
                currentBox.style.display = 'none';
            }
        });
}

function handleRegisterCurrentCamera() {
    if (!currentStatus || !currentStatus.connected || !currentStatus.serial) return;
    
    fetch('/api/cameras/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            serial: currentStatus.serial,
            model: currentStatus.model,
            name: currentStatus.model
        })
    }).then(res => res.json()).then(data => {
        if (data.success) {
            loadRegisteredCameras();
        } else {
            alert('기기 등록 실패: ' + data.error);
        }
    });
}

window.handleDeleteCamera = function(serial) {
    if (!confirm('정말 이 기기를 자동 실행 목록에서 삭제하시겠습니까?')) return;
    
    fetch('/api/cameras/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ serial: serial })
    }).then(res => res.json()).then(data => {
        if (data.success) {
            loadRegisteredCameras();
        }
    });
}

function checkAutorunStatus() {
    const statusText = document.getElementById('autorun-status-text');
    const btnRegister = document.getElementById('btn-autorun-register');
    const btnUnregister = document.getElementById('btn-autorun-unregister');

    statusText.innerText = '확인 중...';
    btnRegister.style.display = 'none';
    btnUnregister.style.display = 'none';
    btnRegister.innerText = '등록';

    fetch('/api/autorun/status')
        .then(res => res.json())
        .then(data => {
            btnRegister.disabled = false;
            btnRegister.title = "";
            
            if (data.is_frozen) {
                btnRegister.disabled = true;
                btnRegister.title = "배포 버전에서는 앱 내 레지스트리 자동 등록을 지원하지 않습니다.";
            }

            if (data.registered) {
                if (data.path_mismatch) {
                    statusText.innerText = '경로 불일치 (현재 경로로 재등록 필요)';
                    statusText.style.color = '#e67e22';
                    btnRegister.innerText = '다시 등록';
                    btnRegister.style.display = 'inline-block';
                    btnUnregister.style.display = 'inline-block';
                } else {
                    statusText.innerText = '등록됨 (활성)';
                    statusText.style.color = 'var(--success-color, #27ae60)';
                    btnUnregister.style.display = 'inline-block';
                }
            } else {
                statusText.innerText = '미등록';
                statusText.style.color = '#e74c3c';
                btnRegister.style.display = 'inline-block';
            }
        })
        .catch(err => {
            statusText.innerText = '상태 확인 실패';
            console.error('Error fetching autorun status:', err);
        });
}

function handleAutorunRegister() {
    fetch('/api/autorun/register', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                checkAutorunStatus();
            } else {
                alert('자동 실행 등록에 실패했습니다. 관리자 권한을 승인했는지 확인하세요.');
            }
        });
}

function handleAutorunUnregister() {
    if (confirm('정말 Windows 레지스트리에서 자동 실행 설정을 삭제하시겠습니까?')) {
        fetch('/api/autorun/unregister', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    checkAutorunStatus();
                } else {
                    alert('자동 실행 삭제에 실패했습니다.');
                }
            });
    }
}

function closeSettingsModal() {
    document.getElementById('modal-settings').classList.add('hidden');
}

function saveSettings() {
    const payload = {
        chkbox_tag: document.getElementById('setting-chkbox-tag').checked,
        chkbox_autorun: document.getElementById('setting-chkbox-autorun').checked,
        chkbox_explorer: document.getElementById('setting-chkbox-explorer').checked,
        save_dir: document.getElementById('setting-save-dir').value.trim(),
        autorun_tag: document.getElementById('setting-autorun-tag').value.trim(),
        autorun_only_registered: document.getElementById('setting-autorun-only-registered').checked
    };

    let changed = false;
    if (originalConfig) {
        if (originalConfig.chkbox_tag !== payload.chkbox_tag ||
            originalConfig.chkbox_autorun !== payload.chkbox_autorun ||
            originalConfig.chkbox_explorer !== payload.chkbox_explorer ||
            (originalConfig.save_dir || '') !== payload.save_dir ||
            (originalConfig.autorun_tag || '') !== payload.autorun_tag ||
            (originalConfig.autorun_only_registered !== payload.autorun_only_registered)) {
            changed = true;
        }
    }

    fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(() => {
        closeSettingsModal();
        if (changed) {
            // 변경된 설정이 적용되기 위해 진행 중이던 모든 작업(스캔/복사)을 초기화하고 메인 화면으로 깔끔하게 돌아갑니다.
            fetch('/api/scan/cancel', { method: 'POST' }).finally(() => {
                isRefreshing = true;
                window.location.reload();
            });
        } else {
            fetchStatus();
        }
    });
}

// Heartbeat to keep backend alive
setInterval(() => { fetch('/api/ping', {method: 'POST'}).catch(e => console.log(e)); }, 2000);
