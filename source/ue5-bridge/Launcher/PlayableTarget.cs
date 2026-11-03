using System.Text.Json;
using System.Text.RegularExpressions;

internal sealed record PlayableTarget(string Project, string Map, string[] EnabledPlugins)
{
    public static PlayableTarget Load(string root)
    {
        string project=Path.Combine(root,"Client/DAoCBridgeClient.uproject");
        string map="/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba";
        string[] plugins=[];
        string file=Path.Combine(root,"playable_project.json");
        if(File.Exists(file))
        {
            using var document=JsonDocument.Parse(File.ReadAllText(file));
            var value=document.RootElement;
            project=Path.GetFullPath(value.GetProperty("project").GetString()
                ?? throw new InvalidDataException("A playable project path is required."),root);
            map=value.GetProperty("map").GetString()
                ?? throw new InvalidDataException("A playable map is required.");
            if(value.TryGetProperty("enable_plugins",out var enabled))
                plugins=enabled.EnumerateArray().Select(x=>x.GetString()
                    ?? throw new InvalidDataException("Plugin names must be strings.")).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        }
        if(!Path.GetExtension(project).Equals(".uproject",StringComparison.OrdinalIgnoreCase)||!File.Exists(project))
            throw new FileNotFoundException("The configured playable Unreal project does not exist.",project);
        if(!Regex.IsMatch(map,@"^/Game/[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*$"))
            throw new InvalidDataException("The playable map must be a /Game package path.");
        if(plugins.Any(x=>!Regex.IsMatch(x,@"^[A-Za-z0-9_]+$")))
            throw new InvalidDataException("The configured plugin name is invalid.");
        string content=Path.Combine(Path.GetDirectoryName(project)!,"Content");
        if(!File.Exists(Path.Combine(content,map[6..].Replace('/',Path.DirectorySeparatorChar)+".umap")))
            throw new FileNotFoundException("The configured playable map is missing from the project.");
        return new PlayableTarget(project,map,plugins);
    }
}
