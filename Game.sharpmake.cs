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
}

[Generate]
public class SharpGameSolution : BaseGameSolution
{
    public SharpGameSolution()
        : base()
    {
        Name = "Drumsmith";

        Globals.FMOD_Win64_Dir = "C:/Program Files (x86)/FMOD SoundSystem/FMOD Studio API Windows/";
        Globals.MONO_Win64_Dir = "";
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