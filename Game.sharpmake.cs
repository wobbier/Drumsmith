using System.IO;
using Sharpmake;

[module: Sharpmake.Include("Engine/Engine.sharpmake.cs")]

[Generate]
public class SharpGameProject : BaseGameProject
{
    public SharpGameProject()
        : base()
    {
        Name = "Drumsmith";
    }
    
    public override void ConfigureAll(Project.Configuration conf, CommonTarget target)
    {
        base.ConfigureAll(conf, target);
                
        conf.IncludePaths.Add(Path.Combine("[project.SharpmakeCsPath]", "ThirdParty/rtmidi"));
        conf.IncludePaths.Add(Path.Combine("[project.SharpmakeCsPath]", "ThirdParty/midifile/include"));
        conf.LibraryPaths.Add(Path.Combine("[project.SharpmakeCsPath]", $@"ThirdParty/Lib/{CommonTarget.GetThirdPartyOptimization(target.Optimization)}"));
        conf.IncludePaths.Add(Path.Combine("[project.SharpmakeCsPath]", "ThirdParty/USB-MIDI/include"));
    }


    public override void ConfigureWin64(Project.Configuration conf, CommonTarget target)
    {
        base.ConfigureWin64(conf, target);
        
        conf.LibraryFiles.Add("rtmidi");
        conf.LibraryFiles.Add("midifile");
        conf.LibraryFiles.Add("winmm.lib");
        conf.LibraryFiles.Add("winhttp.lib");
        //conf.Defines.Add("CPPHTTPLIB_OPENSSL_SUPPORT");

        {
            var copyDirBuildStep = new Configuration.BuildStepCopy(
                Path.Combine(Globals.RootDir, $@"ThirdParty/Bin/{CommonTarget.GetThirdPartyOptimization(target.Optimization)}/"),
                Globals.RootDir + "/.build/[target.Name]");

            copyDirBuildStep.IsFileCopy = false;
            copyDirBuildStep.CopyPattern = "*.dll";
            conf.EventPostBuildExe.Add(copyDirBuildStep);
        }
    }

    public override void ConfigureUWP(Configuration conf, CommonTarget target)
    {
        base.ConfigureUWP(conf, target);
        
        conf.LibraryFiles.Add("rtmidi");
        conf.LibraryFiles.Add("midifile");
        conf.LibraryFiles.Add("winmm.lib");
    }

    public override void ConfigureMac(Configuration conf, CommonTarget target)
    {
        base.ConfigureMac(conf, target);
        conf.IncludePaths.Add("/usr/local/include");
        conf.LibraryPaths.Add("/usr/local/lib");
        conf.LibraryPaths.Add(Path.Combine("[project.SharpmakeCsPath]", "ThirdParty/Lib/macOS/Release"));
        conf.LibraryFiles.Add("curl");
        conf.LibraryFiles.Add("midifile");
        conf.LibraryFiles.Add("rtmidi");
    }
}

[Generate]
public class SharpGameSolution : BaseGameSolution
{
    public SharpGameSolution()
        : base()
    {
        Name = "Drumsmith";

        Globals.FMOD_Win64_Dir = "C:/Program Files (x86)/FMOD SoundSystem/FMOD Studio API Windows/";
        Globals.FMOD_UWP_Dir = "C:/Program Files (x86)/FMOD SoundSystem/FMOD Studio API Universal Windows Platform/";
        Globals.FMOD_macOS_Dir = Util.GetCurrentSharpmakeFileInfo() + "/../ThirdParty/FMOD Programmers API/";
        //Globals.MONO_Win64_Dir = string.Empty;
        Globals.IsPhysicsEnabled3D = true;
        //Globals.ExeName = "Drumsmith";
        System.Console.WriteLine(Globals.FMOD_macOS_Dir);
    }
}

[Generate]
public class UserGameScript : GameScript
{
    public UserGameScript() : base() { }

    public override void ConfigureAll(Configuration conf, CommonTarget target)
    {
        base.ConfigureAll(conf, target);
    }
}

[Generate]
public class UserSharpmakeProject : SharpmakeProjectBase
{
    public UserSharpmakeProject() : base() { }
}
