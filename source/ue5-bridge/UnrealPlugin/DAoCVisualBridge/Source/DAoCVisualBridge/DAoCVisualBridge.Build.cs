using UnrealBuildTool;
public class DAoCVisualBridge : ModuleRules
{
    public DAoCVisualBridge(ReadOnlyTargetRules Target) : base(Target)
    {
        RuntimeDependencies.Add("$(PluginDir)/Content/InterfaceFonts/...", StagedFileType.UFS);
        RuntimeDependencies.Add("$(PluginDir)/Content/ClassicUI/...", StagedFileType.UFS);
        RuntimeDependencies.Add("$(PluginDir)/Content/SpellVisuals_v01/...", StagedFileType.UFS);
        RuntimeDependencies.Add("$(PluginDir)/Content/OriginalAudio_v01/...", StagedFileType.UFS);
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","InputCore"});
        PrivateDependencyModuleNames.AddRange(new string[]{"Sockets","Networking","Json","RenderCore","RHI","Slate","SlateCore","ProceduralMeshComponent"});
    }
}
