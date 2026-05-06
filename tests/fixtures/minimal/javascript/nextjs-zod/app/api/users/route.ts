import { NextRequest, NextResponse } from 'next/server';
import { CreateUserSchema } from '../../../schemas/user';

export async function GET() {
  return NextResponse.json({ users: [] });
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const result = CreateUserSchema.safeParse(body);
  if (!result.success) {
    return NextResponse.json(
      { errors: result.error.flatten() },
      { status: 400 }
    );
  }

  const { name, email, age } = result.data;

  return NextResponse.json({
    success: true,
    user: { id: '123', name, email, age, createdAt: new Date().toISOString() }
  });
}
