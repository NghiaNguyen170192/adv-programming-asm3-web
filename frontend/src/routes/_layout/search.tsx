import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Search, Star } from "lucide-react"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type ItemPublicRow = {
  id: string
  title: string
  brand?: string | null
  description?: string | null
  price?: number | null
  image_url?: string | null
  product_rating?: number | null
  product_rating_count?: number | null
}

type SearchResponse = {
  data: ItemPublicRow[]
  count: number
}

async function searchItems(keyword: string): Promise<SearchResponse> {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/items/search?keyword=${encodeURIComponent(keyword)}&limit=50`,
  )
  if (!response.ok) throw new Error("Search failed")
  return response.json()
}

export const Route = createFileRoute("/_layout/search" as any)({
  component: SearchPage,
  head: () => ({
    meta: [{ title: "Search Products" }],
  }),
})

function SearchPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setIsSearching(true)
    try {
      const data = await searchItems(query.trim())
      setResults(data)
      setHasSearched(true)
    } catch {
      setResults({ data: [], count: 0 })
      setHasSearched(true)
    } finally {
      setIsSearching(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch()
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Search Products</h1>
        <p className="text-muted-foreground mt-1">
          Find cosmetic and beauty products by brand name, product title, or
          description. Supports fuzzy matching for similar keyword forms.
        </p>
      </div>

      {/* Search Bar */}
      <div className="flex gap-2 max-w-2xl">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            className="pl-10"
            placeholder="Search by brand, product name, or keyword..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <Button onClick={handleSearch} disabled={!query.trim() || isSearching}>
          {isSearching ? "Searching..." : "Search"}
        </Button>
      </div>

      {/* Results Count */}
      {hasSearched && results && (
        <div className="text-sm text-muted-foreground">
          Found <span className="font-semibold text-foreground">{results.count}</span>{" "}
          {results.count === 1 ? "product" : "products"} matching &quot;{query}&quot;
        </div>
      )}

      {/* Results Grid */}
      {results && results.data.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {results.data.map((item) => (
            <div
              key={item.id}
              onClick={() => navigate({ to: "/item/$id", params: { id: item.id } })}
              className="cursor-pointer rounded-lg border bg-card p-4 shadow-sm transition-all hover:shadow-md hover:border-primary/50"
            >
              {/* Image placeholder */}
              {item.image_url ? (
                <img
                  src={item.image_url}
                  alt={item.title}
                  className="w-full h-40 object-cover rounded-md mb-3"
                />
              ) : (
                <div className="w-full h-40 bg-muted rounded-md mb-3 flex items-center justify-center">
                  <span className="text-muted-foreground text-xs">No image</span>
                </div>
              )}

              {/* Brand */}
              {item.brand && (
                <p className="text-xs font-medium text-primary uppercase tracking-wide mb-1">
                  {item.brand}
                </p>
              )}

              {/* Title */}
              <h3 className="font-medium text-sm line-clamp-2 mb-2">{item.title}</h3>

              {/* Rating & Price row */}
              <div className="flex items-center justify-between mt-auto">
                <div className="flex items-center gap-1">
                  {item.product_rating != null && (
                    <>
                      <Star className="size-3.5 fill-amber-400 text-amber-400" />
                      <span className="text-xs font-medium">
                        {item.product_rating.toFixed(1)}
                      </span>
                      {item.product_rating_count != null && (
                        <span className="text-xs text-muted-foreground">
                          ({item.product_rating_count})
                        </span>
                      )}
                    </>
                  )}
                </div>
                {item.price != null && (
                  <span className="text-sm font-semibold">
                    ₹{item.price.toFixed(0)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No results */}
      {hasSearched && results && results.data.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Search className="size-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium">No products found</p>
          <p className="text-sm">Try a different keyword or check spelling</p>
        </div>
      )}
    </div>
  )
}
