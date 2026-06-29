export interface Product {
  id: number;
  name: string;
  price: number;
  original_price: number;
  discount_pct: number;
  rating: number;
  review_count: number;
  category: string;
  rank: number;
  source: "jumia" | "marjane";
  url: string;
  image_url: string;
  scraped_at: string;
}

export interface BestsellersResponse {
  total: number;
  items: Product[];
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface DateCount {
  date: string;
  count: number;
}

export interface Stats {
  total: number;
  sources: number;
  categories: number;
  max_discount: number;
  avg_rating: number;
  last_scraped: string;
}
