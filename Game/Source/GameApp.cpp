#include <GameApp.h>
#include <Engine/Engine.h>

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

}

void GameApp::OnEnd()
{
}

void GameApp::PreRender()
{

}

void GameApp::OnInitialize()
{
	GetEngine().LoadScene("Assets/MainMenu.lvl");
}

void GameApp::PostRender()
{
}