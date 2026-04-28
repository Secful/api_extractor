// Next.js App Router - Basic CRUD endpoints

interface User {
  id: string;
  name: string;
  email: string;
}

export async function GET() {
  return Response.json({ users: [] });
}

export async function POST(request: Request) {
  const body = await request.json();
  return Response.json({ success: true, user: body });
}
