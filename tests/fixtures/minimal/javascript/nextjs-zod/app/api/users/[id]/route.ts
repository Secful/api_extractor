import { NextRequest, NextResponse } from 'next/server';
import { UpdateUserSchema, UserResponseSchema } from '../../../../schemas/user';

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(request: NextRequest, { params }: RouteContext) {
  const { id } = await params;

  return NextResponse.json({
    id,
    name: 'John Doe',
    email: 'john@example.com',
    createdAt: new Date().toISOString()
  });
}

export async function PUT(request: NextRequest, { params }: RouteContext) {
  const { id } = await params;
  const body = await request.json();

  const result = UpdateUserSchema.safeParse(body);
  if (!result.success) {
    return NextResponse.json(
      { errors: result.error.flatten() },
      { status: 400 }
    );
  }

  return NextResponse.json({
    id,
    ...result.data,
    createdAt: new Date().toISOString()
  });
}

export async function DELETE(request: NextRequest, { params }: RouteContext) {
  const { id } = await params;

  return new NextResponse(null, { status: 204 });
}
