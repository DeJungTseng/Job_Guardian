'use client';

import { Thread } from '@/components/assistant-ui/thread';

export default function Page() {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gray-50 font-sans">
      <div className="flex h-[600px] w-[1000px] flex-col overflow-hidden rounded-xl border border-gray-300 bg-white">
        <Thread />
      </div>
    </div>
  );
}
