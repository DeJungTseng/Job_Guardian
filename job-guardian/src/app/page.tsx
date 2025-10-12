"use client";

import { Thread } from "@assistant-ui/react";

export default function Page() {
  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#f9fafb",
        fontFamily: "sans-serif",
      }}
    >
      <div
        style={{
          width: "400px",
          height: "600px",
          border: "1px solid #ddd",
          borderRadius: "12px",
          overflow: "hidden",
          background: "white",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ flex: 1, padding: "1em", overflowY: "auto" }}>
          <Thread />
        </div>
      </div>
    </div>
  );
}
