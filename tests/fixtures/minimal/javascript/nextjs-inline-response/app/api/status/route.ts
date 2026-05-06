import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  return NextResponse.json({
    status: "ok",
    timestamp: Date.now(),
    version: "1.0.0"
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  return NextResponse.json({
    received: body,
    processed: true,
    id: "abc-123"
  });
}
