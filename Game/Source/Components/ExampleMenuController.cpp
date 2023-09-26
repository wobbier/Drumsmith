#include <Components/ExampleMenuController.h>

#include <Events/SceneEvents.h>

ExampleMenuController::ExampleMenuController()
	: BasicUIView("ExampleMenuController")
{
	FilePath = Path("Assets/UI/SongList.html");
}

void ExampleMenuController::OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller)
{
	BasicUIView::OnUILoad(GlobalWindow, Caller);

    GlobalWindow["LoadScene"] = BindJSCallback( &ExampleMenuController::LoadScene );
    ExecuteScript( "ClearTrackList();" );

    {
        Path dlcTest = Path( "Assets/DLC/ExampleSong/Album.png" );
        std::string songImage = dlcTest.GetLocalPathString();
        ExecuteScript( "AddTrack('C++', '" + songImage + "'); " );
    }
    {
        Path dlcTest = Path( "Assets/DLC/ExampleSong2/Album.png" );
        std::string songImage = dlcTest.GetLocalPathString();
        ExecuteScript( "AddTrack('test2', '" + songImage + "'); " );
    }
}

void ExampleMenuController::LoadScene(const ultralight::JSObject& thisObject, const ultralight::JSArgs& args)
{
	LoadSceneEvent evt;
	ultralight::String path = args[0].ToString();
	evt.Level = std::string(path.utf8().data());
	evt.Fire();
}