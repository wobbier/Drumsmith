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


    public override void ConfigureWin64(Project.Configuration conf, CommonTarget target)
    {
        base.ConfigureWin64(conf, target);
        conf.Defines.Add("LIBREMIDI_HEADER_ONLY");
        conf.Defines.Add("LIBREMIDI_NO_BOOST");
        conf.ExportDefines.Add("LIBREMIDI_HEADER_ONLY");
        conf.ExportDefines.Add("LIBREMIDI_NO_BOOST");
        conf.IncludePaths.Add(Path.Combine("[project.SharpmakeCsPath]", "ThirdParty/libremidi/include"));
        conf.IncludePaths.Add(Path.Combine("[project.SharpmakeCsPath]", "ThirdParty/USB-MIDI/include"));
        conf.LibraryFiles.Add("winmm.lib");
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
    }
}

[Generate]
public class UserGameScript : GameScript
{
    public UserGameScript() : base() { }
}

[Generate]
public class UserSharpmakeProject : SharpmakeProjectBase
{
    public UserSharpmakeProject() : base() { }
}