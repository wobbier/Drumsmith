#pragma once
#include <Components/UI/BasicUIView.h>

class VocalsTestComponent final
	: public BasicUIView
{
public:
    VocalsTestComponent();
    ~VocalsTestComponent();

#if USING( ME_UI )
    void OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller ) final;
    void OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller ) final;

    void OnUpdate( float dt ) override;

#endif
};

ME_REGISTER_COMPONENT( VocalsTestComponent );