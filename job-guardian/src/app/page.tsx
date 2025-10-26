'use client';

import { Thread } from '@/components/assistant-ui/thread';

export default function Page() {
  return (
    <div className="flex h-screen w-screen flex-col items-center bg-gray-50 font-sans">
      {/* 上方區塊：Assistant-UI 聊天介面 */}
      <div className="flex flex-1 items-center justify-center border-b border-gray-300 bg-white w-full">
        <div className="h-[600px] w-[1000px] overflow-hidden rounded-xl border border-gray-300 shadow-sm">
          <Thread />
        </div>
      </div>

      {/* 下方區塊：Telemetry iframe */}
      <div className="flex h-[220px] w-full items-center justify-center bg-white">
        <div className="w-[1000px] flex items-center justify-center">
          <iframe
            src="http://localhost:5001/telemetry/stream"
            width="100%"
            height="180"
            className="rounded-lg border border-gray-700 shadow-inner"
            style={{
              backgroundColor: '#0d1117',
              colorScheme: 'dark',
            }}
          />
        </div>
      </div>
    </div>
  );
}
