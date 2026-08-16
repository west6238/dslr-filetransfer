using System;
using System.Linq;
using System.IO;
using MediaDevices;

namespace WpdDeleter
{
    class Program
    {
        static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: WpdDeleter.exe <DeviceName>");
                return;
            }

            string targetDeviceName = args[0];
            var devices = MediaDevice.GetDevices();
            var device = devices.FirstOrDefault(d => d.FriendlyName != null && d.FriendlyName.Contains(targetDeviceName, StringComparison.OrdinalIgnoreCase));

            if (device == null)
            {
                Console.WriteLine($"Error: Device '{targetDeviceName}' not found.");
                Environment.Exit(1);
            }

            try
            {
                device.Connect();
                Console.WriteLine($"Connected to {device.FriendlyName}");
                
                var drives = device.GetDrives();
                int deletedCount = 0;
                
                string[] mediaExtensions = {
                    ".jpg", ".jpeg", ".jpe", ".png", ".gif", ".bmp", ".webp", ".nef", ".cr2", ".arw", ".dng",
                    ".mp4", ".mov", ".avi", ".wmv", ".mkv", ".m4v", ".3gp", ".3g2", ".mpg", ".mpeg", ".mts", ".m2ts"
                };

                foreach (var drive in drives)
                {
                    deletedCount += TraverseAndDelete(device, drive.RootDirectory.FullName, mediaExtensions);
                }

                Console.WriteLine($"Delete complete. {deletedCount} files removed.");
                device.Disconnect();
                Environment.Exit(0);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                Environment.Exit(1);
            }
        }

        static int TraverseAndDelete(MediaDevice device, string path, string[] extensions)
        {
            int deletedCount = 0;
            try
            {
                var files = device.GetFiles(path);
                foreach (var file in files)
                {
                    string ext = Path.GetExtension(file).ToLower();
                    if (extensions.Contains(ext))
                    {
                        device.DeleteFile(file);
                        deletedCount++;
                        Console.WriteLine($"Deleted: {file}");
                    }
                }

                var directories = device.GetDirectories(path);
                foreach (var dir in directories)
                {
                    deletedCount += TraverseAndDelete(device, dir, extensions);
                }
            }
            catch (Exception)
            {
                // Ignore errors for individual files/folders
            }

            return deletedCount;
        }
    }
}
