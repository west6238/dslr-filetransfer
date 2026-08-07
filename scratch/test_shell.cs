using System;
using System.IO;
using Shell32; // or dynamic

class Program
{
    static void Main()
    {
        Type shellType = Type.GetTypeFromProgID("Shell.Application");
        dynamic shell = Activator.CreateInstance(shellType);
        dynamic drives = shell.NameSpace(17); // ssfDRIVES

        foreach (dynamic d in drives.Items())
        {
            if (d.Name == "D90")
            {
                Console.WriteLine("Found D90 device");
                dynamic folder = d.GetFolder;
                ListItems(folder, 0);
            }
        }
    }

    static void ListItems(dynamic folder, int depth)
    {
        string indent = new string(' ', depth * 2);
        dynamic items = folder.Items();
        Console.WriteLine($"{indent}Folder: {folder.Title} (Count: {items.Count})");

        foreach (dynamic item in items)
        {
            Console.WriteLine($"{indent}- {item.Name} (IsFolder: {item.IsFolder})");
            if (item.IsFolder)
            {
                try
                {
                    dynamic subFolder = item.GetFolder;
                    if (subFolder != null)
                    {
                        ListItems(subFolder, depth + 1);
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"{indent}  Error: {ex.Message}");
                }
            }
        }
    }
}
