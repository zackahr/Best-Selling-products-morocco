"use client";
import Image from "next/image";
import { Product } from "@/types/product";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function Stars({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <span className="flex items-center gap-0.5 text-yellow-400 text-sm">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i}>
          {i < full ? "★" : i === full && half ? "½" : "☆"}
        </span>
      ))}
      <span className="text-gray-400 text-xs ml-1">{rating.toFixed(1)}</span>
    </span>
  );
}

export default function ProductCard({ product }: { product: Product }) {
  const imgSrc = product.image_url
    ? `${API}/api/image?url=${encodeURIComponent(product.image_url)}`
    : "/placeholder.png";

  return (
    <a
      href={product.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 flex flex-col overflow-hidden"
    >
      {/* image */}
      <div className="relative h-44 bg-gray-50 flex items-center justify-center overflow-hidden">
        <Image
          src={imgSrc}
          alt={product.name}
          fill
          className="object-contain p-3 group-hover:scale-105 transition-transform duration-200"
          unoptimized
        />
        {product.discount_pct > 0 && (
          <span className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            -{Math.round(product.discount_pct)}%
          </span>
        )}
        <span
          className={`absolute top-2 right-2 text-white text-xs font-semibold px-2 py-0.5 rounded-full ${
            product.source === "jumia" ? "bg-orange-500" : "bg-green-600"
          }`}
        >
          {product.source === "jumia" ? "Jumia" : "Marjane"}
        </span>
      </div>

      {/* info */}
      <div className="p-3 flex flex-col gap-1.5 flex-1">
        <span className="text-xs font-medium text-indigo-600 bg-indigo-50 rounded-full px-2 py-0.5 self-start truncate max-w-full">
          {product.category}
        </span>
        <p className="text-sm font-medium text-gray-800 line-clamp-2 leading-snug">
          {product.name}
        </p>
        <div className="flex items-baseline gap-2 mt-auto pt-1">
          <span className="text-base font-bold text-gray-900">
            {product.price.toLocaleString("fr-MA")} DH
          </span>
          {product.original_price > product.price && (
            <span className="text-xs text-gray-400 line-through">
              {product.original_price.toLocaleString("fr-MA")} DH
            </span>
          )}
        </div>
        {product.rating > 0 && <Stars rating={product.rating} />}
        {product.review_count > 0 && (
          <span className="text-xs text-gray-400">
            {product.review_count.toLocaleString()} avis
          </span>
        )}
      </div>
    </a>
  );
}
