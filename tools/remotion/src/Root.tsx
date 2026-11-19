import React from 'react';
import {Composition, staticFile} from 'remotion';
import {SmokeTest} from './SmokeTest';
import {TalkingHead} from './TalkingHead';
import {GraphicsDemo, DEMO, DEMO_FACE, DEMO_FOOTAGE} from './GraphicsDemo';
import {PitchFinal} from './pitch/PitchFinal';
import {PitchV4} from './pitch/PitchV4';
import {parseMedia} from '@remotion/media-parser';
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="PitchFinal" component={PitchV4} fps={30} width={1920} height={1080} durationInFrames={2226}
      defaultProps={{plate: 'pitch/plate_look_v4.mp4', plateBlur: 'pitch/plate_look_v4_blur34.mp4', audio: 'pitch/mix_v3.wav', voice: 'pitch/voice_master_v3.wav', showGuides: false}} />
    <Composition id="PitchFinalV1" component={PitchFinal} fps={30} width={1920} height={1080} durationInFrames={2400}
      defaultProps={{plate: 'pitch/plate.mp4', plateBlur: 'pitch/plate_blur34.mp4', voice: 'pitch/voice_master.wav', showGuides: false}} />
    <Composition id="SmokeTest" component={SmokeTest} durationInFrames={90} fps={30} width={1920} height={1080}
      defaultProps={{title: 'Accelerating AI Infrastructure', subtitle: 'Jane Doe · VP Engineering'}} />
    <Composition id="SmokeTest4K" component={SmokeTest} durationInFrames={90} fps={30} width={3840} height={2160}
      defaultProps={{title: 'Accelerating AI Infrastructure', subtitle: 'Jane Doe · VP Engineering'}} />
    <Composition id="Bench10s" component={SmokeTest} durationInFrames={300} fps={30} width={1920} height={1080} defaultProps={{title: "Accelerating AI Infrastructure", subtitle: "Bench"}} />
    <Composition id="Bench10s4K" component={SmokeTest} durationInFrames={300} fps={30} width={3840} height={2160} defaultProps={{title: "Accelerating AI Infrastructure", subtitle: "Bench"}} />
    <Composition id="Overlay4K" component={SmokeTest} durationInFrames={300} fps={30} width={3840} height={2160} defaultProps={{title: "Accelerating AI Infrastructure", subtitle: "Overlay only", withVideo: false}} />
    <Composition id="Overlay1080" component={SmokeTest} durationInFrames={300} fps={30} width={1920} height={1080} defaultProps={{title: "Accelerating AI Infrastructure", subtitle: "Overlay only", withVideo: false}} />
    <Composition id="TalkingHead" component={TalkingHead} fps={30} width={1920} height={1080} durationInFrames={150}
      defaultProps={{src: 'cut.mp4', captionsSrc: 'captions.json', name: 'JANE DOE', role: 'VP ENGINEERING, DDN'}}
      calculateMetadata={async ({props}) => {
        const {slowDurationInSeconds} = await parseMedia({src: staticFile(props.src), fields: {slowDurationInSeconds: true}, acknowledgeRemotionLicense: true});
        return {durationInFrames: Math.ceil(slowDurationInSeconds * 30)};
      }} />
    <Composition id="TalkingHead4K" component={TalkingHead} fps={30} width={3840} height={2160} durationInFrames={150}
      defaultProps={{src: 'cut.mp4', captionsSrc: 'captions.json', name: 'JANE DOE', role: 'VP ENGINEERING, DDN'}} />
    <Composition id="GraphicsDemo" component={GraphicsDemo} fps={30} width={1920} height={1080}
      durationInFrames={Math.ceil((DEMO.total + 1.5) * 30)}
      defaultProps={{footage: DEMO_FOOTAGE, faceBox: DEMO_FACE, avoid: [], showProgress: true, showTimer: true, logos: true}} />
    <Composition id="GraphicsDemoText" component={GraphicsDemo} fps={30} width={1920} height={1080}
      durationInFrames={Math.ceil((DEMO.total + 1.5) * 30)}
      defaultProps={{footage: DEMO_FOOTAGE, faceBox: DEMO_FACE, avoid: [], showProgress: true, showTimer: true, logos: false}} />
    <Composition id="GraphicsOverlay" component={GraphicsDemo} fps={30} width={1920} height={1080}
      durationInFrames={Math.ceil((DEMO.total + 1.5) * 30)}
      defaultProps={{footage: null, faceBox: DEMO_FACE, avoid: [], showProgress: true, showTimer: true, logos: true}} />
  </>
);
