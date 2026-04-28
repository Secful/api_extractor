// Next.js App Router - Dynamic route with path parameter

interface User {
  id: string;
  name: string;
  email: string;
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return Response.json({ user: { id, name: "John", email: "john@example.com" } });
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();
  return Response.json({ success: true, user: { id, ...body } });
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return Response.json({ success: true, deleted: id });
}
