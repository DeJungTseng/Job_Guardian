// src/components/assistant-ui/tool-fallback.tsx
"use client";

import type { ToolCallMessagePartComponent } from "@assistant-ui/react";
import { useState } from "react";
// 你可能還要引入 Button 或 Icon，但這些不是 function props
export const ToolFallback: ToolCallMessagePartComponent = (props) => {
  // 不要接收 function props，做最簡化版本
  return <div>（無工具）</div>;
};
