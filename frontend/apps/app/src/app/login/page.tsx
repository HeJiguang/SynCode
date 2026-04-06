"use client";

import * as React from "react";
import { CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { frontendPreviewMode } from "@aioj/config";
import { setBrowserAccessToken } from "@aioj/api";
import { Button, Input, Panel } from "@aioj/ui";
import { appApiPath, appInternalPath } from "../../lib/paths";

type Point = {
  x: number;
  y: number;
};

type MascotId = "tiny" | "cap" | "leader" | "balloon" | "peek";
type MascotMood = "curious" | "leader" | "sleepy" | "shy" | "peek" | "balloon";
type MascotPersonality = "scout" | "spark" | "steady" | "grumpy" | "aloof";

type MascotProps = {
  id: MascotId;
  personality: MascotPersonality;
  x: number;
  baseY: number;
  height: number;
  width: number;
  lowerLean: number;
  upperLean: number;
  stroke: string;
  accent: string;
  eye: string;
  faceStroke: string;
  mood: MascotMood;
  bodyPointer: Point;
  headPointer: Point;
  eyePointer: Point;
  pointerVelocity: number;
  frame: number;
  emailFocused: boolean;
  passwordFocused: boolean;
  trackStrength: number;
  hoverRadius: number;
  pointerLag: number;
  emailProbeStrength: number;
  codeAvoidStrength: number;
  angerGain: number;
  recoilStrength: number;
  coldness: number;
  shake: number;
  onClick: () => void;
};

const SCENE_WIDTH = 620;
const SCENE_HEIGHT = 560;

const mascotProfiles: Omit<MascotProps, "bodyPointer" | "headPointer" | "eyePointer" | "pointerVelocity" | "frame" | "emailFocused" | "passwordFocused" | "shake" | "onClick">[] = [
  {
    id: "tiny",
    personality: "scout",
    x: 116,
    baseY: 514,
    height: 112,
    width: 18,
    lowerLean: -10,
    upperLean: -18,
    stroke: "var(--mascot-stroke)",
    accent: "rgba(110,231,183,0.54)",
    eye: "var(--mascot-eye)",
    faceStroke: "var(--mascot-face)",
    mood: "peek",
    trackStrength: 0.9,
    hoverRadius: 0.16,
    pointerLag: 0.18,
    emailProbeStrength: 0.58,
    codeAvoidStrength: 0.92,
    angerGain: 0.08,
    recoilStrength: 0.9,
    coldness: 0.08
  },
  {
    id: "cap",
    personality: "spark",
    x: 196,
    baseY: 518,
    height: 196,
    width: 44,
    lowerLean: -14,
    upperLean: -30,
    stroke: "var(--mascot-stroke)",
    accent: "rgba(45,212,191,0.62)",
    eye: "var(--mascot-eye)",
    faceStroke: "var(--mascot-face)",
    mood: "curious",
    trackStrength: 1.42,
    hoverRadius: 0.24,
    pointerLag: 0.02,
    emailProbeStrength: 1.28,
    codeAvoidStrength: 0.34,
    angerGain: 0.14,
    recoilStrength: 0.18,
    coldness: 0.02
  },
  {
    id: "leader",
    personality: "steady",
    x: 334,
    baseY: 522,
    height: 252,
    width: 34,
    lowerLean: -2,
    upperLean: -6,
    stroke: "var(--mascot-stroke)",
    accent: "rgba(16,185,129,0.78)",
    eye: "var(--mascot-eye)",
    faceStroke: "var(--mascot-face)",
    mood: "leader",
    trackStrength: 1.08,
    hoverRadius: 0.22,
    pointerLag: 0.04,
    emailProbeStrength: 0.48,
    codeAvoidStrength: 0.08,
    angerGain: 0,
    recoilStrength: 0.08,
    coldness: 0.08
  },
  {
    id: "balloon",
    personality: "grumpy",
    x: 462,
    baseY: 516,
    height: 174,
    width: 28,
    lowerLean: 8,
    upperLean: 22,
    stroke: "var(--mascot-stroke)",
    accent: "rgba(20,184,166,0.62)",
    eye: "var(--mascot-eye)",
    faceStroke: "var(--mascot-face)",
    mood: "balloon",
    trackStrength: 0.62,
    hoverRadius: 0.2,
    pointerLag: 0.08,
    emailProbeStrength: 0.24,
    codeAvoidStrength: 1.24,
    angerGain: 1.1,
    recoilStrength: 0.3,
    coldness: 0.16
  },
  {
    id: "peek",
    personality: "aloof",
    x: 550,
    baseY: 512,
    height: 126,
    width: 14,
    lowerLean: 4,
    upperLean: 16,
    stroke: "var(--mascot-stroke)",
    accent: "rgba(153,246,228,0.54)",
    eye: "var(--mascot-eye)",
    faceStroke: "var(--mascot-face)",
    mood: "sleepy",
    trackStrength: 0.34,
    hoverRadius: 0.14,
    pointerLag: 0.42,
    emailProbeStrength: 0.18,
    codeAvoidStrength: 0.52,
    angerGain: 0,
    recoilStrength: 0.12,
    coldness: 0.8
  }
];

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function mix(a: number, b: number, t: number) {
  return a * (1 - t) + b * t;
}

function distance(a: Point, b: Point) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function SceneMascot({
  personality,
  baseY,
  accent,
  emailFocused,
  eye,
  faceStroke,
  height,
  hoverRadius,
  lowerLean,
  mood,
  onClick,
  pointerLag,
  passwordFocused,
  bodyPointer,
  headPointer,
  eyePointer,
  pointerVelocity,
  frame,
  recoilStrength,
  shake,
  stroke,
  trackStrength,
  upperLean,
  width,
  x,
  emailProbeStrength,
  codeAvoidStrength,
  angerGain,
  coldness
}: MascotProps) {
  const anchor = {
    x: x / SCENE_WIDTH,
    y: (baseY - height * 0.76) / SCENE_HEIGHT
  };
  const bodyFollowPointer = {
    x: mix(bodyPointer.x, 0.5, pointerLag),
    y: mix(bodyPointer.y, 0.46, pointerLag * 0.92)
  };
  const headFollowPointer = {
    x: mix(headPointer.x, 0.5, pointerLag * 0.45),
    y: mix(headPointer.y, 0.46, pointerLag * 0.38)
  };
  const eyeFollowPointer = {
    x: eyePointer.x,
    y: eyePointer.y
  };
  const avoidPointer = {
    x: clamp(anchor.x - (0.14 + codeAvoidStrength * 0.08), 0.08, 0.42),
    y: clamp(anchor.y - 0.08 - coldness * 0.02, 0.12, 0.72)
  };
  const bodyFocusTarget = passwordFocused
    ? avoidPointer
    : emailFocused
      ? { x: 0.79, y: 0.34 }
      : bodyFollowPointer;
  const headFocusTarget = passwordFocused
    ? avoidPointer
    : emailFocused
      ? { x: 0.79, y: 0.34 }
      : headFollowPointer;
  const eyeFocusTarget = passwordFocused
    ? avoidPointer
    : emailFocused
      ? { x: 0.79, y: 0.34 }
      : eyeFollowPointer;
  const hoverInfluence = clamp(1 - distance(headPointer, anchor) / hoverRadius, 0, 1);
  const anger = clamp((hoverInfluence - 0.16) * angerGain, 0, 1);
  const emailProbe = emailFocused ? emailProbeStrength : 0;
  const codeAvoid = passwordFocused ? codeAvoidStrength : 0;
  const recoilDirection = headPointer.x > anchor.x ? -1 : 1;
  const recoil = hoverInfluence * recoilStrength * (1 - emailProbe * 0.22);
  const motionFactor = clamp(0.34 + hoverInfluence * 0.66 + pointerVelocity * 0.4, 0.2, 1.36);
  const sceneActivity = clamp(
    hoverInfluence * 0.45 + emailProbe * 0.7 + codeAvoid * 0.45 + pointerVelocity * 0.72,
    0,
    1
  );
  const bodyLookDx = bodyFocusTarget.x - anchor.x;
  const bodyLookDy = bodyFocusTarget.y - anchor.y;
  const headLookDx = headFocusTarget.x - anchor.x;
  const headLookDy = headFocusTarget.y - anchor.y;
  const eyeLookDx = eyeFocusTarget.x - anchor.x;
  const eyeLookDy = eyeFocusTarget.y - anchor.y;
  const idlePrimary =
    Math.sin(frame * 0.12 + x * 0.01 + baseY * 0.015 + eyePointer.x * 1.4) * (0.08 + sceneActivity * 0.24);
  const idleSecondary =
    Math.cos(frame * 0.09 + x * 0.016 + baseY * 0.01 + eyePointer.y * 1.1) * (0.06 + sceneActivity * 0.2);
  const pointerLift = emailProbe * 10 + idleSecondary * Math.max(0.35, width * 0.018) - recoil * 2;
  const bodyLean =
    idlePrimary * Math.max(0.5, width * 0.028) +
    bodyLookDx * 38 * trackStrength * motionFactor +
    emailProbe * 16 -
    codeAvoid * 20 +
    recoil * 12 * recoilDirection +
    anger * 10;
  const bodyCurve =
    idleSecondary * Math.max(0.8, width * 0.05) +
    bodyLookDx * 46 * trackStrength * motionFactor +
    emailProbe * 10 -
    codeAvoid * 14 +
    anger * 7;
  const upperShift =
    upperLean +
    bodyLean * 0.28 +
    (emailFocused ? (mood === "curious" ? -16 : mood === "leader" ? 9 : mood === "peek" ? -7 : 0) : 0) +
    (passwordFocused ? (mood === "balloon" ? -22 : mood === "sleepy" ? -8 : mood === "peek" ? -10 : 0) : 0);

  const topY = baseY - height - pointerLift;
  const path = `M 0 ${baseY}
    C ${lowerLean * 0.12 + bodyCurve * 0.18} ${baseY - 38} ${lowerLean * 0.22 + bodyCurve * 0.2} ${baseY - 92} ${lowerLean * 0.28 + bodyCurve * 0.24} ${baseY - 144}
    C ${lowerLean * 0.32 + bodyCurve * 0.26} ${baseY - 202} ${upperShift * 0.42 + bodyLean * 0.14} ${topY + 96} ${upperShift} ${topY}`;

  const faceX = upperShift + bodyLean * 0.18 + (passwordFocused && mood === "balloon" ? -10 : 0);
  const faceY = topY + (width > 40 ? 24 : 20) - emailProbe * 4 + codeAvoid * 2;
  const eyeDx = clamp(eyeLookDx * 26 * trackStrength - codeAvoid * 8 + anger * 4, -6.2, 6.2);
  const eyeDy = clamp(eyeLookDy * 14 * trackStrength - emailProbe * 1.4, -4.2, 4.2);
  const closed = passwordFocused && (mood === "sleepy" || mood === "balloon" || personality === "grumpy");
  const eyeY = faceY - 2 - anger * 1.2;
  const smileY = faceY + 9;
  const headRx = Math.max(12, width * (0.34 + coldness * 0.03));
  const headRy = Math.max(10, width * 0.24);
  const headTilt = clamp(
    idlePrimary * 1.8 + headLookDx * 18 * trackStrength - codeAvoid * 22 + anger * 16 - recoil * 8 * recoilDirection,
    -24,
    24
  );
  const upperBodyRotate = clamp(
    idlePrimary * 1.2 +
      headLookDx * 22 * trackStrength -
      codeAvoid * 36 -
      anger * 12 -
      recoil * 6 * recoilDirection,
    -34,
    18
  );
  const torsoPivotX = upperShift * 0.5 + bodyLean * 0.08;
  const torsoPivotY = topY + Math.max(54, height * 0.56);
  const shoulderY = torsoPivotY - Math.max(22, width * 0.9);
  const mouthLift =
    personality === "spark"
      ? 4
      : personality === "grumpy"
        ? -6 * anger - 2
        : personality === "aloof"
          ? -1
          : 2;
  const halfWidth = Math.max(10, width * 0.48);
  const capRadius = Math.max(12, width * 0.42);
  const hitLeft = Math.min(-halfWidth - 28, upperShift - halfWidth - 24, faceX - headRx - 24);
  const hitRight = Math.max(halfWidth + 28, upperShift + halfWidth + 24, faceX + headRx + 24);
  const hitTop = Math.min(topY - headRy - 28, faceY - headRy - 24);
  const hitBottom = baseY + Math.max(30, width * 0.9);
  const bodyOutline = `M ${-halfWidth} ${baseY - capRadius}
    C ${-halfWidth + lowerLean * 0.04} ${baseY - height * 0.3}
      ${upperShift - halfWidth + lowerLean * 0.02 + bodyCurve * 0.08} ${topY + height * 0.16}
      ${upperShift - halfWidth} ${topY + capRadius}
    A ${halfWidth} ${capRadius} 0 0 1 ${upperShift + halfWidth} ${topY + capRadius}
    C ${upperShift + halfWidth - lowerLean * 0.02 - bodyCurve * 0.08} ${topY + height * 0.16}
      ${halfWidth - lowerLean * 0.04} ${baseY - height * 0.3}
      ${halfWidth} ${baseY - capRadius}
    A ${halfWidth} ${capRadius} 0 0 1 ${-halfWidth} ${baseY - capRadius}`;
  const centerLine = `M 0 ${baseY - capRadius * 0.6}
    C ${lowerLean * 0.08} ${baseY - height * 0.3}
      ${upperShift * 0.48} ${topY + height * 0.18}
      ${upperShift} ${topY + capRadius * 0.9}`;

  return (
    <g transform={`translate(${x + shake} 0)`} className="cursor-pointer" onClick={onClick}>
      <rect
        x={hitLeft}
        y={hitTop}
        width={hitRight - hitLeft}
        height={hitBottom - hitTop}
        rx={Math.max(18, width * 0.8)}
        fill="transparent"
        pointerEvents="all"
      />
      <path d={bodyOutline} fill="none" stroke={stroke} strokeLinejoin="round" strokeWidth="3.2" />
      <path
        d={centerLine}
        fill="none"
        stroke={accent}
        strokeLinecap="round"
        strokeWidth="1.6"
        strokeDasharray={mood === "leader" ? "1 0" : "8 10"}
      />
      <path
        d={path}
        fill="none"
        stroke={accent}
        strokeLinecap="round"
        strokeWidth="1.2"
        strokeOpacity="0.24"
      />
      <ellipse
        cx={bodyLean * 0.08}
        cy={baseY + 2}
        rx={halfWidth * (1.02 + hoverInfluence * 0.06)}
        ry={Math.max(3, width * 0.12)}
        fill="none"
        stroke="rgba(45,212,191,0.12)"
        strokeWidth="1"
      />
      <g transform={`rotate(${upperBodyRotate} ${torsoPivotX} ${torsoPivotY})`}>
        <path
          d={`M ${torsoPivotX} ${torsoPivotY} C ${torsoPivotX + bodyCurve * 0.08} ${torsoPivotY - 26} ${faceX - 3} ${shoulderY + 18} ${faceX} ${shoulderY}`}
          fill="none"
          stroke={stroke}
          strokeLinecap="round"
          strokeWidth="2.2"
        />
        <path
          d={`M ${faceX - headRx * 0.72} ${shoulderY + 6} C ${faceX - headRx * 0.32} ${shoulderY - 1} ${faceX + headRx * 0.32} ${shoulderY - 1} ${faceX + headRx * 0.72} ${shoulderY + 6}`}
          fill="none"
          stroke={accent}
          strokeLinecap="round"
          strokeWidth="1.35"
          strokeOpacity="0.58"
        />

        {personality === "spark" ? (
        <path
          d={`M ${faceX + headRx * 0.12} ${faceY + headRy * 0.88} C ${faceX + headRx * 0.7} ${faceY + headRy * 0.96} ${faceX + headRx * 1.08 + emailProbe * 10} ${faceY + headRy * 0.74} ${faceX + headRx * 1.36 + emailProbe * 10} ${faceY + headRy * 0.18}`}
          fill="none"
          stroke={accent}
          strokeLinecap="round"
          strokeWidth="1.55"
        />
        ) : null}

        {personality === "steady" ? (
        <>
          <path
            d={`M ${faceX - headRx * 0.5} ${faceY + headRy * 0.8} C ${faceX - headRx * 1.24} ${faceY + headRy * 0.9} ${faceX - headRx * 1.48} ${faceY + headRy * 0.34} ${faceX - headRx * 1.62} ${faceY - 8}`}
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="1.45"
            strokeOpacity="0.72"
          />
          <path
            d={`M ${faceX + headRx * 0.5} ${faceY + headRy * 0.8} C ${faceX + headRx * 1.24} ${faceY + headRy * 0.9} ${faceX + headRx * 1.48} ${faceY + headRy * 0.34} ${faceX + headRx * 1.62} ${faceY - 8}`}
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="1.45"
            strokeOpacity="0.72"
          />
        </>
        ) : null}

        {personality === "grumpy" ? (
        <>
          <path
            d={`M ${faceX - headRx * 0.16} ${faceY + headRy * 0.96} C ${faceX - headRx * 0.82 - codeAvoid * 10} ${faceY + headRy * 1.08} ${faceX - headRx * 0.96 - codeAvoid * 10} ${faceY + headRy * 0.34} ${faceX - headRx * 1.16 - codeAvoid * 10} ${faceY - 3}`}
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="1.65"
          />
          <path
            d={`M ${faceX + headRx * 0.08} ${faceY + headRy * 0.96} C ${faceX + headRx * 0.78} ${faceY + headRy * 1.02} ${faceX + headRx * 0.92} ${faceY + headRy * 0.5} ${faceX + headRx * 1.02} ${faceY + 4}`}
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="1.65"
          />
        </>
        ) : null}

        {mood === "curious" ? (
        <>
          <path
            d={`M ${faceX - 18} ${topY + 5} C ${faceX - 6} ${topY - 9} ${faceX + 20} ${topY - 9} ${faceX + 28} ${topY + 6}`}
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="2.8"
          />
          <path
            d={`M ${faceX - 32} ${topY + 10} H ${faceX + 18} C ${faceX + 28} ${topY + 10} ${faceX + 32} ${topY + 16} ${faceX + 32} ${topY + 24} V ${topY + 28} H ${faceX - 38} V ${topY + 24} C ${faceX - 38} ${topY + 14} ${faceX - 34} ${topY + 10} ${faceX - 32} ${topY + 10}`}
            fill="none"
            stroke={accent}
            strokeWidth="1.6"
            strokeOpacity="0.58"
          />
        </>
        ) : null}

        {mood === "leader" ? (
        <path
          d={`M ${faceX - 18} ${topY + 8} C ${faceX - 8} ${topY - 2} ${faceX + 12} ${topY - 4} ${faceX + 22} ${topY + 6}`}
          fill="none"
          stroke={accent}
          strokeLinecap="round"
          strokeWidth="2.8"
        />
        ) : null}

        <ellipse cx={faceX} cy={faceY} rx={headRx} ry={headRy} fill="none" stroke={faceStroke} strokeWidth="2.2" />

        {personality === "scout" ? (
        <path
          d={`M ${faceX - 2} ${faceY - headRy + 1} C ${faceX - 5} ${faceY - headRy - 10 - hoverInfluence * 4} ${faceX + 4} ${faceY - headRy - 14 - hoverInfluence * 4} ${faceX + 6} ${faceY - headRy - 20 - hoverInfluence * 6}`}
          fill="none"
          stroke={accent}
          strokeLinecap="round"
          strokeWidth="1.35"
        />
        ) : null}

        {personality === "aloof" ? (
        <path
          d={`M ${faceX - headRx + 2} ${faceY - headRy + 8} C ${faceX - headRx * 0.45} ${faceY - headRy + 2} ${faceX + headRx * 0.2} ${faceY - headRy + 2} ${faceX + headRx - 5} ${faceY - headRy + 10}`}
          fill="none"
          stroke={accent}
          strokeLinecap="round"
          strokeWidth="1.2"
          strokeOpacity="0.46"
        />
        ) : null}

        {closed ? (
        <>
          <path
            d={`M ${faceX - 12} ${eyeY} C ${faceX - 8} ${eyeY + 3} ${faceX - 2} ${eyeY + 3} ${faceX + 2} ${eyeY}`}
            fill="none"
            stroke={eye}
            strokeLinecap="round"
            strokeWidth="1.9"
          />
          <path
            d={`M ${faceX + 6} ${eyeY} C ${faceX + 10} ${eyeY + 3} ${faceX + 16} ${eyeY + 3} ${faceX + 20} ${eyeY}`}
            fill="none"
            stroke={eye}
            strokeLinecap="round"
            strokeWidth="1.9"
          />
        </>
        ) : mood === "peek" ? (
        <>
          {anger > 0.08 || personality === "aloof" ? (
            <>
              <path
                d={`M ${faceX - headRx * 0.54} ${faceY - headRy * 0.22 - anger * 3} C ${faceX - headRx * 0.34} ${faceY - headRy * 0.48 - anger * 4 - coldness} ${faceX - headRx * 0.08} ${faceY - headRy * 0.3 + coldness * 2} ${faceX + headRx * 0.08} ${faceY - headRy * 0.22 + coldness * 2}`}
                fill="none"
                stroke={accent}
                strokeLinecap="round"
                strokeWidth="1.3"
                strokeOpacity={0.44 + anger * 0.44}
              />
              <path
                d={`M ${faceX + headRx * 0.02} ${faceY - headRy * 0.22 + coldness * 2} C ${faceX + headRx * 0.24} ${faceY - headRy * 0.36 + coldness * 2} ${faceX + headRx * 0.42} ${faceY - headRy * 0.46 - anger * 4} ${faceX + headRx * 0.64} ${faceY - headRy * 0.18 - anger * 3}`}
                fill="none"
                stroke={accent}
                strokeLinecap="round"
                strokeWidth="1.3"
                strokeOpacity={0.44 + anger * 0.44}
              />
            </>
          ) : null}
          <circle cx={faceX - 4 + eyeDx} cy={eyeY + eyeDy} r="3.2" fill="none" stroke={faceStroke} strokeWidth="1.5" />
          <circle cx={faceX + 10 + eyeDx} cy={eyeY + eyeDy} r="3.2" fill="none" stroke={faceStroke} strokeWidth="1.5" />
          <circle cx={faceX - 4 + eyeDx} cy={eyeY + eyeDy} r="1.2" fill={eye} />
          <circle cx={faceX + 10 + eyeDx} cy={eyeY + eyeDy} r="1.2" fill={eye} />
        </>
        ) : (
        <>
          {anger > 0.08 ? (
            <>
              <path
                d={`M ${faceX - 16} ${eyeY - 9 - anger * 2} C ${faceX - 10} ${eyeY - 14 - anger * 4} ${faceX - 1} ${eyeY - 10 + coldness} ${faceX + 3} ${eyeY - 8 + coldness}`}
                fill="none"
                stroke={accent}
                strokeLinecap="round"
                strokeWidth="1.35"
              />
              <path
                d={`M ${faceX + 2} ${eyeY - 8 + coldness} C ${faceX + 8} ${eyeY - 10 + coldness} ${faceX + 14} ${eyeY - 14 - anger * 4} ${faceX + 20} ${eyeY - 9 - anger * 2}`}
                fill="none"
                stroke={accent}
                strokeLinecap="round"
                strokeWidth="1.35"
              />
            </>
          ) : null}
          <circle cx={faceX - 8 + eyeDx} cy={eyeY + eyeDy} r="3.4" fill="none" stroke={faceStroke} strokeWidth="1.6" />
          <circle cx={faceX + 8 + eyeDx} cy={eyeY + eyeDy} r="3.4" fill="none" stroke={faceStroke} strokeWidth="1.6" />
          <circle cx={faceX - 8 + eyeDx} cy={eyeY + eyeDy} r="1.2" fill={eye} />
          <circle cx={faceX + 8 + eyeDx} cy={eyeY + eyeDy} r="1.2" fill={eye} />
        </>
        )}

        <path
          d={
            mood === "peek"
              ? `M ${faceX - 6} ${smileY} C ${faceX - 2} ${smileY + 2 + mouthLift - anger * 2} ${faceX + 2} ${smileY + 2 + mouthLift - anger * 2} ${faceX + 6} ${smileY}`
              : mood === "leader"
                ? `M ${faceX - 10} ${smileY} C ${faceX - 3} ${smileY + 5 + mouthLift - anger * 2} ${faceX + 5} ${smileY + 5 + mouthLift - anger * 2} ${faceX + 12} ${smileY}`
                : `M ${faceX - 9} ${smileY} C ${faceX - 3} ${smileY + 4 + mouthLift - anger * 2} ${faceX + 3} ${smileY + 4 + mouthLift - anger * 2} ${faceX + 9} ${smileY}`
          }
          fill="none"
          stroke={accent}
          strokeLinecap="round"
          strokeWidth="1.7"
        />

        {mood === "balloon" ? (
        <>
          <circle
            cx={faceX + 54 + shake * 0.25 + anger * 4}
            cy={faceY - 18}
            r={14 + Math.max(0, Math.sin(eyePointer.x * Math.PI + baseY * 0.01)) * 2}
            fill="none"
            stroke={accent}
            strokeWidth="1.7"
          />
          <path
            d={`M ${faceX + 18} ${faceY + 4} C ${faceX + 30} ${faceY - 4} ${faceX + 40} ${faceY - 12} ${faceX + 50} ${faceY - 18}`}
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="1.6"
          />
          <circle cx={faceX + 14} cy={faceY + 2} r="4.5" fill="none" stroke={faceStroke} strokeWidth="1.4" />
        </>
        ) : null}
      </g>
    </g>
  );
}

const MascotCanvas = React.memo(function MascotCanvas({
  emailFocused,
  passwordFocused
}: {
  emailFocused: boolean;
  passwordFocused: boolean;
}) {
  const [motion, setMotion] = React.useState({
    bodyPointer: { x: 0.5, y: 0.5 },
    headPointer: { x: 0.5, y: 0.5 },
    eyePointer: { x: 0.5, y: 0.5 },
    velocity: 0,
    frame: 0
  });
  const [lightTheme, setLightTheme] = React.useState(false);
  const [wiggles, setWiggles] = React.useState<Record<MascotId, number>>({} as Record<MascotId, number>);
  const stageRef = React.useRef<HTMLDivElement | null>(null);
  const pointerTargetRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const bodyTargetRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const headTargetRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const eyeTargetRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const bodyCurrentRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const headCurrentRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const eyeCurrentRef = React.useRef<Point>({ x: 0.5, y: 0.5 });
  const velocityRef = React.useRef(0);
  const rafIdRef = React.useRef<number | null>(null);
  const lastTickRef = React.useRef(0);
  const frameTimeRef = React.useRef(0);
  const wigglesRef = React.useRef<Record<MascotId, number>>({} as Record<MascotId, number>);

  const ensureAnimationLoop = React.useCallback(() => {
    if (rafIdRef.current !== null) return;

    const tick = (now: number) => {
      const previousTime = lastTickRef.current || now;
      const deltaMs = Math.min(34, now - previousTime || 16);
      lastTickRef.current = now;
      frameTimeRef.current += deltaMs / 16.67;

      const bodyFollowWeight = 0.34;
      const headFollowWeight = 0.62;
      const eyeFollowWeight = 0.92;
      bodyTargetRef.current = {
        x: mix(0.5, pointerTargetRef.current.x, bodyFollowWeight),
        y: mix(0.48, pointerTargetRef.current.y, bodyFollowWeight * 0.72)
      };
      headTargetRef.current = {
        x: mix(0.5, pointerTargetRef.current.x, headFollowWeight),
        y: mix(0.46, pointerTargetRef.current.y, headFollowWeight * 0.82)
      };
      eyeTargetRef.current = {
        x: mix(0.5, pointerTargetRef.current.x, eyeFollowWeight),
        y: mix(0.46, pointerTargetRef.current.y, eyeFollowWeight * 0.92)
      };

      const bodyCurrent = bodyCurrentRef.current;
      const headCurrent = headCurrentRef.current;
      const eyeCurrent = eyeCurrentRef.current;
      const bodyTarget = bodyTargetRef.current;
      const headTarget = headTargetRef.current;
      const eyeTarget = eyeTargetRef.current;
      const bodyStep = clamp((deltaMs / 16.67) * 0.08, 0.045, 0.14);
      const headStep = clamp((deltaMs / 16.67) * 0.14, 0.08, 0.24);
      const eyeStep = clamp((deltaMs / 16.67) * 0.24, 0.14, 0.36);
      const nextBodyPointer = {
        x: bodyCurrent.x + (bodyTarget.x - bodyCurrent.x) * bodyStep,
        y: bodyCurrent.y + (bodyTarget.y - bodyCurrent.y) * bodyStep
      };
      const nextHeadPointer = {
        x: headCurrent.x + (headTarget.x - headCurrent.x) * headStep,
        y: headCurrent.y + (headTarget.y - headCurrent.y) * headStep
      };
      const nextEyePointer = {
        x: eyeCurrent.x + (eyeTarget.x - eyeCurrent.x) * eyeStep,
        y: eyeCurrent.y + (eyeTarget.y - eyeCurrent.y) * eyeStep
      };
      const rawVelocity = clamp(distance(nextEyePointer, eyeCurrent) * 18, 0, 1);
      const nextVelocity = velocityRef.current + (rawVelocity - velocityRef.current) * 0.24;
      const wiggleActive = Object.values(wigglesRef.current).some((start) => frameTimeRef.current - start < 20);
      const pointerSettled =
        distance(nextBodyPointer, bodyTarget) < 0.0008 &&
        distance(nextHeadPointer, headTarget) < 0.0007 &&
        distance(nextEyePointer, eyeTarget) < 0.0006;
      const velocitySettled = nextVelocity < 0.0025;

      bodyCurrentRef.current = nextBodyPointer;
      headCurrentRef.current = nextHeadPointer;
      eyeCurrentRef.current = nextEyePointer;
      velocityRef.current = nextVelocity;

      setMotion({
        bodyPointer: nextBodyPointer,
        headPointer: nextHeadPointer,
        eyePointer: nextEyePointer,
        velocity: nextVelocity,
        frame: frameTimeRef.current
      });

      if (pointerSettled && velocitySettled && !wiggleActive) {
        rafIdRef.current = null;
        return;
      }

      rafIdRef.current = window.requestAnimationFrame(tick);
    };

    lastTickRef.current = performance.now();
    rafIdRef.current = window.requestAnimationFrame(tick);
  }, []);

  React.useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        window.cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  React.useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: light)");

    function syncTheme() {
      const root = document.documentElement;
      const isLight = root.classList.contains("light") || (!root.classList.contains("dark") && media.matches);
      setLightTheme(isLight);
    }

    syncTheme();
    media.addEventListener("change", syncTheme);

    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    return () => {
      media.removeEventListener("change", syncTheme);
      observer.disconnect();
    };
  }, []);

  function triggerWiggle(id: MascotId) {
    const next = { ...wigglesRef.current, [id]: frameTimeRef.current };
    wigglesRef.current = next;
    setWiggles(next);
    ensureAnimationLoop();
  }

  function getWiggle(id: MascotId) {
    const start = wiggles[id];
    if (start === undefined) return 0;
    const progress = motion.frame - start;
    if (progress > 20) return 0;
    return Math.sin((progress / 20) * Math.PI * 4) * (1 - progress / 20) * 6;
  }

  const updatePointerTarget = React.useCallback((clientX: number, clientY: number) => {
    const bounds = stageRef.current?.getBoundingClientRect();
    if (!bounds) return;

    const nextTarget = {
      x: clamp((clientX - bounds.left) / bounds.width, 0.08, 0.92),
      y: clamp((clientY - bounds.top) / bounds.height, 0.1, 0.84)
    };
    if (distance(nextTarget, pointerTargetRef.current) < 0.0035) return;
    pointerTargetRef.current = nextTarget;
    ensureAnimationLoop();
  }, [ensureAnimationLoop]);

  React.useEffect(() => {
    function handleWindowPointerMove(event: PointerEvent) {
      updatePointerTarget(event.clientX, event.clientY);
    }

    window.addEventListener("pointermove", handleWindowPointerMove);
    return () => window.removeEventListener("pointermove", handleWindowPointerMove);
  }, [updatePointerTarget]);

  const handleWindowLeave = React.useCallback(() => {
    pointerTargetRef.current = { x: 0.5, y: 0.5 };
    ensureAnimationLoop();
  }, [ensureAnimationLoop]);

  React.useEffect(() => {
    window.addEventListener("blur", handleWindowLeave);
    return () => window.removeEventListener("blur", handleWindowLeave);
  }, [handleWindowLeave]);

  React.useEffect(() => {
    ensureAnimationLoop();
  }, [emailFocused, passwordFocused, ensureAnimationLoop]);

  const blink = Math.sin(motion.frame * 0.11) > 0.92;

  const scene = lightTheme
    ? {
        outer: "linear-gradient(180deg,rgba(244,247,252,0.98),rgba(236,241,249,0.96))",
        inner: "linear-gradient(180deg,rgba(249,251,255,0.98),rgba(241,245,251,0.96))",
        frameStroke: "rgba(132,150,181,0.18)",
        guideStroke: "rgba(132,150,181,0.1)",
        ringStroke: "rgba(132,150,181,0.18)",
        plaqueFill: "rgba(255,255,255,0.22)",
        plaqueStroke: "rgba(132,150,181,0.22)",
        plaqueText: "rgba(92,111,147,0.78)",
        floorLine: "rgba(117,136,171,0.2)",
        floorShadow: "rgba(156,171,196,0.18)",
        mascotStroke: "rgba(95,113,143,0.9)",
        faceStroke: "rgba(112,123,155,0.9)",
        eye: "rgba(92,111,147,0.86)"
      }
    : {
        outer: "linear-gradient(180deg,rgba(19,20,20,0.98),rgba(11,12,12,0.97))",
        inner: "linear-gradient(180deg,rgba(20,25,24,0.98),rgba(14,18,17,0.96))",
        frameStroke: "rgba(94,234,212,0.1)",
        guideStroke: "rgba(94,234,212,0.06)",
        ringStroke: "rgba(45,212,191,0.1)",
        plaqueFill: "rgba(255,255,255,0.02)",
        plaqueStroke: "rgba(45,212,191,0.12)",
        plaqueText: "rgba(204,251,241,0.5)",
        floorLine: "rgba(45,212,191,0.12)",
        floorShadow: "rgba(45,212,191,0.06)",
        mascotStroke: "rgba(226,232,240,0.78)",
        faceStroke: "rgba(203,213,225,0.72)",
        eye: "rgba(240,253,250,0.84)"
      };

  return (
    <div
      ref={stageRef}
      className="syncode-login-mascot relative h-full min-h-[620px] overflow-hidden rounded-[28px] border border-[var(--border-soft)] p-4"
      style={
        {
          background: scene.outer,
          "--mascot-stroke": scene.mascotStroke,
          "--mascot-face": scene.faceStroke,
          "--mascot-eye": scene.eye
        } as React.CSSProperties
      }
    >
      <div
        className="relative h-full min-h-[560px] overflow-hidden rounded-[26px] border border-[var(--border-soft)] shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
        style={{ background: scene.inner }}
      >
        <svg className="line-art-scene absolute inset-0 h-full w-full" viewBox="0 0 620 560" fill="none">
          <rect x="24" y="22" width="572" height="516" rx="28" stroke={scene.frameStroke} strokeWidth="1.4" />
          <path d="M68 170c82-58 174-82 276-76 86 4 168 30 242 76" stroke={scene.guideStroke} strokeWidth="0.9" />
          <circle cx="332" cy="196" r="142" stroke={scene.ringStroke} strokeWidth="1.15" strokeDasharray="10 18" />

          <g className="syncode-track-wordmark" transform="rotate(3 420 118)">
            <path
              d="M158 138c92-28 202-36 310-18 74 12 142 34 190 64"
              stroke={scene.guideStroke}
              strokeWidth="0.9"
              strokeLinecap="round"
            />
            <text
              x="360"
              y="110"
              fill="none"
              stroke={scene.plaqueText}
              strokeWidth="0.95"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.72"
              fontSize="38"
              fontWeight="600"
              letterSpacing="0.1em"
              fontFamily="Geist, Inter, PingFang SC, Microsoft YaHei, sans-serif"
            >
              SynCode
            </text>
          </g>

          <path d="M36 516c108-18 216-19 286-13 96 8 190 8 260-7" stroke={scene.floorLine} strokeWidth="1.65" />
          <ellipse cx="310" cy="530" rx="176" ry="12" stroke={scene.floorShadow} strokeWidth="1" />
          {mascotProfiles.map((profile) => (
            <SceneMascot
              key={profile.id}
              {...profile}
              bodyPointer={motion.bodyPointer}
              headPointer={motion.headPointer}
              eyePointer={motion.eyePointer}
              pointerVelocity={motion.velocity}
              frame={motion.frame}
              emailFocused={emailFocused}
              passwordFocused={passwordFocused}
              shake={getWiggle(profile.id)}
              onClick={() => triggerWiggle(profile.id)}
            />
          ))}
        </svg>
      </div>
    </div>
  );
});

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [status, setStatus] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [emailFocused, setEmailFocused] = React.useState(false);
  const [codeFocused, setCodeFocused] = React.useState(false);

  async function sendCode() {
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(appApiPath("/auth/send-code"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "发送验证码失败。");
      }

      setStatus("验证码已发送，请检查邮箱。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "发送验证码失败。");
    } finally {
      setLoading(false);
    }
  }

  async function login() {
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(appApiPath("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "登录失败。");
      }

      setBrowserAccessToken(payload.token);
      router.push(appInternalPath("/"));
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "登录失败。");
    } finally {
      setLoading(false);
    }
  }

  const statusTone = status?.includes("失败") ? "text-[var(--danger)]" : "text-[var(--success)]";

  return (
    <main className="min-h-screen bg-[var(--bg)] px-4 py-6 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-[1440px] gap-3 lg:grid-cols-[1fr_1fr]">
        <Panel className="hero-grid hidden overflow-hidden bg-[var(--surface-2)] p-4 md:p-6 lg:flex lg:items-center lg:justify-center lg:p-7" tone="strong">
          <div className="h-full w-full">
            <MascotCanvas emailFocused={emailFocused} passwordFocused={codeFocused} />
          </div>
        </Panel>

        <Panel className="relative flex items-center justify-center overflow-hidden p-5 md:p-8" tone="strong">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-[-8%] top-[10%] h-48 w-48 rounded-full bg-[var(--accent-bg)] blur-3xl opacity-60" />
            <div className="absolute right-[-6%] top-[22%] h-40 w-40 rounded-full bg-[var(--accent-wash)] blur-3xl opacity-55" />
            <div className="absolute inset-[14px] rounded-[calc(var(--radius-card)-6px)] border border-[var(--border-soft)] opacity-70" />
          </div>

          <div className="relative z-10 w-full max-w-[500px]">
            <p className="kicker">Access</p>
            <h2 className="mt-3 text-3xl font-semibold text-[var(--text-primary)]">登录 SynCode</h2>

            {frontendPreviewMode ? (
              <div className="mt-4 rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-3 text-sm leading-7 text-[var(--text-secondary)]">
                当前本地已开启前端预览模式。你可以不登录，直接进入工作台查看和修改界面。
              </div>
            ) : null}

            <div className="mt-6 rounded-[22px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-5">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--text-faint)]" htmlFor="email">
                    Email
                  </label>
                  <Input
                    id="email"
                    autoComplete="email"
                    placeholder="输入邮箱地址"
                    value={email}
                    onFocus={() => setEmailFocused(true)}
                    onBlur={() => setEmailFocused(false)}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--text-faint)]" htmlFor="code">
                    Verification Code
                  </label>
                  <div className="grid gap-3 md:grid-cols-[1fr_132px]">
                    <Input
                      id="code"
                      inputMode="numeric"
                      placeholder="输入验证码"
                      value={code}
                      onFocus={() => setCodeFocused(true)}
                      onBlur={() => setCodeFocused(false)}
                      onChange={(event) => setCode(event.target.value)}
                    />
                    <Button disabled={loading || !email} variant="secondary" onClick={sendCode}>
                      发送验证码
                    </Button>
                  </div>
                </div>

                <Button className="w-full" disabled={loading || !email || !code} size="lg" onClick={login}>
                  登录并进入工作台
                </Button>

                {frontendPreviewMode ? (
                  <Button className="w-full" variant="secondary" size="lg" onClick={() => router.push(appInternalPath("/"))}>
                    直接进入预览模式
                  </Button>
                ) : null}

                {status ? (
                  <div className="flex items-start gap-3 rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
                    <CheckCircle2 size={16} className={`mt-0.5 shrink-0 ${statusTone}`} />
                    <p className={`text-sm leading-7 ${statusTone}`}>{status}</p>
                  </div>
                ) : null}
              </div>
            </div>

            <p className="mt-4 text-xs leading-6 text-[var(--text-muted)]">
              验证码会发送到你的邮箱。若暂未收到，请先确认邮箱地址可用，再重新发送。
            </p>
          </div>
        </Panel>
      </div>
    </main>
  );
}
