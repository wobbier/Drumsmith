#pragma once
#include <ECS/Core.h>
#include "Components/Audio/AudioSource.h"

class AudioCore;
namespace FMOD { class DSP; }
namespace FMOD { class Channel; }
namespace FMOD { class Sound; }
namespace FMOD { class System; }

class VocalsTestCore final
	: public Core<VocalsTestCore>
{
public:
	VocalsTestCore();
	~VocalsTestCore();

	virtual void Init() final;

	virtual void OnEntityAdded(Entity& NewEntity) final;
    virtual void OnEntityRemoved( Entity& InEntity ) final;

    void OnAddedToWorld() override;
    void OnRemovedFromWorld() override;

    void OnStop() override;

    virtual void Update( const UpdateContext& context ) final;

    void OnStart() override;
    void ProcessFFT();

private:
#if USING( ME_EDITOR )
	virtual void OnEditorInspect() final;
#endif

    AudioCore* audioCore = nullptr;
    FMOD::System* audioSystem = nullptr;
    FMOD::Sound* sound = nullptr;
    FMOD::Channel* channel = nullptr;
    FMOD::DSP* fftDsp = nullptr;
    SharedPtr<Sound> testVocals;
    int mappedValue = 0;
    float smoothedPitch = 0.0f;
};

ME_REGISTER_CORE(VocalsTestCore)
