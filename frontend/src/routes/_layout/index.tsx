import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { BadgePercent, Clock, Package, Plus, Sparkles, Star } from "lucide-react"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"

type RecItem = {
  id: string
  title: string
  brand?: string | null
  image_url?: string | null
  price?: number | null
  mrp?: number | null
  product_rating?: number | null
  product_rating_count?: number | null
  score?: number
  review_count?: number
  original_price?: number
  discounted_price?: number
  discount_pct?: number
}

type HomepageRecs = {
  chosen_for_you: RecItem[]
  chosen_strategy: string
  new_arrivals: RecItem[]
  best_offers: RecItem[]
}

function authHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
    "Content-Type": "application/json",
  }
}

async function fetchHomepageRecs(): Promise<HomepageRecs> {
  const res = await fetch(
    `${OpenAPI.BASE}/api/v1/items/homepage-recommendations`,
    { headers: authHeaders() },
  )
  if (!res.ok) return { chosen_for_you: [], chosen_strategy: "cold_start", new_arrivals: [], best_offers: [] }
  return res.json()
}

async function addToCart(itemId: string): Promise<void> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/${itemId}?quantity=1`, {
    method: "POST",
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error("Failed to add to cart")
}

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [{ title: "Dashboard" }],
  }),
})

const STRATEGY_LABELS: Record<string, string> = {
  cold_start: "Popular picks to get you started",
  warm_start: "Based on your reviews and taste",
  hot_start: "Matched to your cart + preferences",
}

function Dashboard() {
  const { user: currentUser } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: recs, isLoading } = useQuery({
    queryKey: ["homepage-recs"],
    queryFn: fetchHomepageRecs,
  })

  const cartMutation = useMutation({
    mutationFn: addToCart,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] })
      queryClient.invalidateQueries({ queryKey: ["homepage-recs"] })
      showSuccessToast("Added to cart")
    },
    onError: (e: Error) => showErrorToast(e.message),
  })

  const chosen = recs?.chosen_for_you ?? []
  const newArrivals = recs?.new_arrivals ?? []
  const offers = recs?.best_offers ?? []
  const strategy = recs?.chosen_strategy ?? "cold_start"

  return (
    <div className="flex flex-col gap-8 pb-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-light tracking-tight">
          Welcome, <span className="font-semibold">{currentUser?.full_name || currentUser?.email}</span>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Discover beauty products curated just for you
        </p>
      </div>

      {isLoading && (
        <p className="text-muted-foreground text-sm">Loading recommendations...</p>
      )}

      {/* ── CHOSEN FOR YOU ──────────────────────────────────── */}
      {chosen.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="size-4" />
            <h2 className="text-sm font-semibold uppercase tracking-widest">Chosen For You</h2>
            <span className="text-xs px-2 py-0.5 rounded-full border font-medium text-muted-foreground">
              {strategy.replace("_", " ")}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            {STRATEGY_LABELS[strategy] || "Personalized recommendations"}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {chosen.map((item) => (
              <div
                key={item.id}
                className="group rounded-none border-0 border-b bg-card transition-all hover:opacity-80 flex flex-col"
              >
                <div
                  className="cursor-pointer p-3 flex-1"
                  onClick={() => navigate({ to: "/item/$id", params: { id: item.id } } as any)}
                >
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.title} className="w-full h-36 object-cover mb-3" />
                  ) : (
                    <div className="w-full h-36 bg-muted mb-3 flex items-center justify-center">
                      <Package className="size-8 text-muted-foreground/40" />
                    </div>
                  )}
                  {item.brand && (
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">{item.brand}</p>
                  )}
                  <h3 className="text-xs line-clamp-2 mb-1">{item.title}</h3>
                  <div className="flex items-baseline gap-1.5 mt-auto">
                    {item.price != null && (
                      <span className="text-sm font-semibold">₹{item.price.toFixed(0)}</span>
                    )}
                    {item.mrp != null && item.price != null && item.mrp > item.price && (
                      <span className="text-xs text-muted-foreground line-through">₹{item.mrp.toFixed(0)}</span>
                    )}
                  </div>
                  {item.product_rating != null && item.product_rating > 0 && (
                    <div className="flex items-center gap-1 mt-1">
                      <Star className="size-3 fill-foreground text-foreground" />
                      <span className="text-[10px] text-muted-foreground">{item.product_rating.toFixed(1)}</span>
                    </div>
                  )}
                </div>
                <div className="px-3 pb-3">
                  <Button
                    size="sm"
                    className="w-full text-xs rounded-none"
                    disabled={cartMutation.isPending}
                    onClick={() => cartMutation.mutate(item.id)}
                  >
                    <Plus className="size-3 mr-1" /> Add to Bag
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── NEW ARRIVALS ────────────────────────────────────── */}
      {newArrivals.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-1">
            <Clock className="size-4" />
            <h2 className="text-sm font-semibold uppercase tracking-widest">New Arrivals</h2>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Just dropped — discover them before everyone else
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {newArrivals.map((item) => (
              <div
                key={item.id}
                className="group rounded-none border-0 border-b bg-card transition-all hover:opacity-80 flex flex-col"
              >
                <div
                  className="cursor-pointer p-3 flex-1"
                  onClick={() => navigate({ to: "/item/$id", params: { id: item.id } } as any)}
                >
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.title} className="w-full h-36 object-cover mb-3" />
                  ) : (
                    <div className="w-full h-36 bg-muted mb-3 flex items-center justify-center">
                      <Package className="size-8 text-muted-foreground/40" />
                    </div>
                  )}
                  {item.brand && (
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">{item.brand}</p>
                  )}
                  <h3 className="text-xs line-clamp-2 mb-1">{item.title}</h3>
                  <div className="flex items-baseline gap-1.5">
                    {item.price != null && (
                      <span className="text-sm font-semibold">₹{item.price.toFixed(0)}</span>
                    )}
                  </div>
                  {item.review_count != null && (
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {item.review_count === 0 ? "No reviews yet" : `${item.review_count} review(s)`}
                    </p>
                  )}
                </div>
                <div className="px-3 pb-3">
                  <Button
                    size="sm"
                    className="w-full text-xs rounded-none"
                    disabled={cartMutation.isPending}
                    onClick={() => cartMutation.mutate(item.id)}
                  >
                    <Plus className="size-3 mr-1" /> Add to Bag
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── BEST OFFER ──────────────────────────────────────── */}
      {offers.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-1">
            <BadgePercent className="size-4" />
            <h2 className="text-sm font-semibold uppercase tracking-widest">Best Offers</h2>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Exclusive deals — limited time 20% off
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {offers.map((item) => (
              <div
                key={item.id}
                className="group rounded-none border-0 border-b bg-card transition-all hover:opacity-80 flex flex-col"
              >
                <div
                  className="cursor-pointer p-3 flex-1 relative"
                  onClick={() => navigate({ to: "/item/$id", params: { id: item.id } } as any)}
                >
                  <span className="absolute top-2 right-2 text-[10px] font-bold text-white bg-foreground px-2 py-0.5 z-10">
                    -{item.discount_pct}%
                  </span>
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.title} className="w-full h-36 object-cover mb-3" />
                  ) : (
                    <div className="w-full h-36 bg-muted mb-3 flex items-center justify-center">
                      <Package className="size-8 text-muted-foreground/40" />
                    </div>
                  )}
                  {item.brand && (
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">{item.brand}</p>
                  )}
                  <h3 className="text-xs line-clamp-2 mb-1">{item.title}</h3>
                  <div className="flex items-baseline gap-2">
                    {item.discounted_price != null && (
                      <span className="text-sm font-semibold">₹{item.discounted_price.toFixed(0)}</span>
                    )}
                    {item.original_price != null && (
                      <span className="text-xs text-muted-foreground line-through">₹{item.original_price.toFixed(0)}</span>
                    )}
                  </div>
                </div>
                <div className="px-3 pb-3">
                  <Button
                    size="sm"
                    className="w-full text-xs rounded-none"
                    disabled={cartMutation.isPending}
                    onClick={() => cartMutation.mutate(item.id)}
                  >
                    <Plus className="size-3 mr-1" /> Add to Bag
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
