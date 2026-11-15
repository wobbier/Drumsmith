#include <GameApp.h>
#include <Engine/Engine.h>
#include "Core/CommandLine.h"
#include "CoreGame/TrackList.h"

GameApp::GameApp(int argc, char** argv)
	: Game(argc, argv)
{
}

GameApp::~GameApp()
{
}

void GameApp::OnStart()
{

}

void GameApp::OnUpdate(const UpdateContext& inUpdateContext)
{
	// The menu controllers tick from MenuCore, declared in each menu scene (Docs/UI-and-Menus.md).
}

void GameApp::OnEnd()
{
}

void GameApp::PreRender()
{

}

void GameApp::OnInitialize()
{
	// --convert-dlc: what Settings > Convert Custom DLC does, at startup (headless re-charting).
	// Songs edited in the Track Editor keep their charts unless --convert-dlc-force.
	if( CommandLine::Has( "--convert-dlc" ) || CommandLine::Has( "--convert-dlc-force" ) )
	{
		TrackDatabase::GetInstance().ExportMidiTrackMetaData( CommandLine::Has( "--convert-dlc-force" ) );
	}
	GetEngine().LoadScene("Assets/MainMenu.lvl");
}

void GameApp::PostRender()
{
}
