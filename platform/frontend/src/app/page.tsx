"use client";
import { useEffect, useState, useCallback } from "react";
import ProductCard from "@/components/ProductCard";
import FilterBar from "@/components/FilterBar";
import {
  BestsellersResponse,
  CategoryCount,
  DateCount,
  Stats,
  Product,
} from "@/types/product";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PAGE_SIZE = 60;

async function apiFetch<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}

function buildQuery(params: Record<string, string | number>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v !== undefined) p.set(k, String(v));
  }
  return p.toString() ? `?${p.toString()}` : "";
}

export default function Home() {
  const [filters, setFilters] = useState({
    date: "",
    source: "",
    category: "",
    sort: "reviews",
  });
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [categories, setCategories] = useState<CategoryCount[]>([]);
  const [dates, setDates] = useState<DateCount[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<DateCount[]>("/api/dates").then(setDates).catch(console.error);
    apiFetch<Stats>("/api/stats").then(setStats).catch(console.error);
  }, []);

  useEffect(() => {
    const q = buildQuery({
      ...(filters.date && { date: filters.date }),
      ...(filters.source && { source: filters.source }),
    });
    apiFetch<CategoryCount[]>(`/api/categories${q}`)
      .then(setCategories)
      .catch(console.error);
  }, [filters.date, filters.source]);

  const fetchProducts = useCallback(
    async (f: typeof filters, p: number) => {
      setLoading(true);
      try {
        const q = buildQuery({
          ...(f.date && { date: f.date }),
          ...(f.source && { source: f.source }),
          ...(f.category && { category: f.category }),
          sort: f.sort,
          limit: PAGE_SIZE,
          offset: p * PAGE_SIZE,
        });
        const data = await apiFetch<BestsellersResponse>(`/api/bestsellers${q}`);
        setProducts(data.items);
        setTotal(data.total);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    setPage(0);
    fetchProducts(filters, 0);
  }, [filters, fetchProducts]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1">
            <h1 className="text-xl font-bold text-gray-900">
              🇲🇦 Morocco Market Intel
            </h1>
            <p className="text-xs text-gray-500">
              Bestsellers from Jumia &amp; Marjane · updated daily at 11:00
            </p>
          </div>
          {stats && (
            <div className="flex flex-wrap gap-4 text-sm text-gray-600">
              <span>
                <strong className="text-gray-900">
                  {stats.total.toLocaleString()}
                </strong>{" "}
                products
              </span>
              <span>
                <strong className="text-gray-900">{stats.categories}</strong>{" "}
                categories
              </span>
              <span>
                <strong className="text-red-500">
                  -{Math.round(stats.max_discount)}%
                </strong>{" "}
                max deal
              </span>
              <span className="text-gray-400 hidden sm:inline">
                last: {stats.last_scraped}
              </span>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-5">
          <FilterBar
            filters={filters}
            onChange={setFilters}
            categories={categories}
            dates={dates}
          />
        </div>

        <div className="mb-4 text-sm text-gray-500">
          {loading ? "Loading…" : `${total.toLocaleString()} products`}
        </div>

        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-xl h-72 animate-pulse border border-gray-100"
              />
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-24 text-gray-400">
            No products found. Run the scraper first.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <button
              className="px-4 py-2 rounded-lg bg-white border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
              disabled={page === 0}
              onClick={() => {
                const np = page - 1;
                setPage(np);
                fetchProducts(filters, np);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              ← Prev
            </button>
            <span className="px-4 py-2 text-sm text-gray-500">
              {page + 1} / {totalPages}
            </span>
            <button
              className="px-4 py-2 rounded-lg bg-white border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
              disabled={page >= totalPages - 1}
              onClick={() => {
                const np = page + 1;
                setPage(np);
                fetchProducts(filters, np);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              Next →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
