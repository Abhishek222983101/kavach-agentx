import React from "react";
import { Composition } from "remotion";
import { KavachDemo } from "./Video";
import timeline from "./timeline.json";
export const Root: React.FC = () => (
  <Composition id="KavachDemo" component={KavachDemo} durationInFrames={timeline.total} fps={timeline.fps} width={1920} height={1080} />
);
