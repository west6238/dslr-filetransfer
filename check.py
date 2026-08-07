import win32com.client
shell=win32com.client.Dispatch('Shell.Application')
folder=shell.NameSpace(17)
print([(i.Name, i.Path) for i in folder.Items()])
