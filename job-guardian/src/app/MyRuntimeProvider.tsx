"use client";

import type { ReactNode } from "react";
import {
    AssistantRuntimeProvider,
    useLocalRuntime,
    type ChatModelAdapter,
} from "@assistant-ui/react";

const MyModelAdapter: ChatModelAdapter = {
    async run({ messages, abortSignal }) {
        const response = await fetch("http://localhost:8000/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages }),
            signal: abortSignal,
        });

        const data = await response.json();

        return {
            content: [
                {
                    type: "text",
                    text: data.text ?? "🦉 Job Guardian 沒有回應",
                },
            ],
        };
    },
};

export function MyRuntimeProvider({ children }: { children: ReactNode }) {
    const runtime = useLocalRuntime(MyModelAdapter);
    return (
        <AssistantRuntimeProvider runtime={runtime}>
            {children}
        </AssistantRuntimeProvider>
    );
}
