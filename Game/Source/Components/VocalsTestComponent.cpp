#include <Components/VocalsTestComponent.h>


VocalsTestComponent::VocalsTestComponent()
    : BasicUIView( "VocalsTestComponent" )
{
    FilePath = Path( "Assets/UI/DLC_NEW.html" );
}


VocalsTestComponent::~VocalsTestComponent()
{
}


#if USING( ME_UI )

void VocalsTestComponent::OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnJSReady( GlobalWindow, Caller );
}


void VocalsTestComponent::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );
}


void VocalsTestComponent::OnUpdate( float dt )
{

}

#endif