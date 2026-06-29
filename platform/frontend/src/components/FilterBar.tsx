"use client";
import { CategoryCount, DateCount } from "@/types/product";

interface Filters {
  date: string;
  source: string;
  category: string;
  sort: string;
}

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
  categories: CategoryCount[];
  dates: DateCount[];
}

const SORTS = [
  { value: "reviews", label: "Most reviewed" },
  { value: "discount", label: "Biggest discount" },
  { value: "rating", label: "Top rated" },
  { value: "price_asc", label: "Price ↑" },
  { value: "price_desc", label: "Price ↓" },
];

export default function FilterBar({ filters, onChange, categories, dates }: Props) {
  const set = (key: keyof Filters, val: string) =>
    onChange({ ...filters, [key]: val });

  const selectClass =
    "text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 cursor-pointer";

  return (
    <div className="flex flex-wrap gap-3 items-center">
      {/* date */}
      <select
        className={selectClass}
        value={filters.date}
        onChange={(e) => set("date", e.target.value)}
      >
        <option value="">Today</option>
        {dates.map((d) => (
          <option key={d.date} value={d.date}>
            {d.date} ({d.count})
          </option>
        ))}
      </select>

      {/* source */}
      <select
        className={selectClass}
        value={filters.source}
        onChange={(e) => set("source", e.target.value)}
      >
        <option value="">All sources</option>
        <option value="jumia">Jumia</option>
        <option value="marjane">Marjane</option>
      </select>

      {/* category */}
      <select
        className={selectClass}
        value={filters.category}
        onChange={(e) => set("category", e.target.value)}
      >
        <option value="">All categories</option>
        {categories.map((c) => (
          <option key={c.category} value={c.category}>
            {c.category} ({c.count})
          </option>
        ))}
      </select>

      {/* sort */}
      <select
        className={selectClass}
        value={filters.sort}
        onChange={(e) => set("sort", e.target.value)}
      >
        {SORTS.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </div>
  );
}
