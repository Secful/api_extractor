// Next.js Pages Router - Basic endpoints

interface Product {
  id: string;
  name: string;
  price: number;
}

export default function handler(req, res) {
  if (req.method === 'GET') {
    res.status(200).json({ products: [] });
  }
  if (req.method === 'POST') {
    res.status(201).json({ success: true, product: req.body });
  }
}
