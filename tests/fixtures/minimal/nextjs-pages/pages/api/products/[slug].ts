// Next.js Pages Router - Dynamic route

interface Product {
  id: string;
  name: string;
  price: number;
  slug: string;
}

export default function handler(req, res) {
  const { slug } = req.query;

  if (req.method === 'GET') {
    res.status(200).json({ product: { slug, name: "Product", price: 99.99 } });
  }
  if (req.method === 'PUT') {
    res.status(200).json({ success: true, product: { slug, ...req.body } });
  }
  if (req.method === 'DELETE') {
    res.status(200).json({ success: true, deleted: slug });
  }
}
