import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { ArrowLeft, Sparkles, Star, ShoppingCart, Users, FlaskConical, User } from "lucide-react"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"

type ItemDetail = {
  id: string
  title: string
  brand?: string | null
  description?: string | null
  price?: number | null
  mrp?: number | null
  image_url?: string | null
  product_url?: string | null
  product_rating?: number | null
  product_rating_count?: number | null
}

type ReviewRow = {
  id: string
  title: string
  description: string
  rating: number
  review_date?: string | null
  is_a_buyer?: boolean | null
  predicted_is_a_buyer?: boolean | null
  prediction_confidence?: number | null
  owner_name?: string | null
  created_at?: string | null
}

type ReviewsResponse = {
  data: ReviewRow[]
  count: number
}

async function fetchItem(id: string): Promise<ItemDetail> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}/api/v1/items/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error("Item not found")
  return response.json()
}

type SimilarItemsResponse = {
  data: ItemDetail[]
  count: number
}

async function fetchSimilarItems(itemId: string): Promise<SimilarItemsResponse> {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/items/${itemId}/similar?limit=8`,
  )
  if (!response.ok) throw new Error("Failed to load recommendations")
  return response.json()
}

type SkincareItem = ItemDetail & {
  reason?: string
  synergy_ingredient?: string
  co_purchase_count?: number
}

type RoutineStep = {
  step: string
  items: ItemDetail[]
}

type SkincareResponse = {
  item_tags: {
    ingredients: string[]
    skin_types: string[]
    concerns: string[]
    product_steps: string[]
  }
  perfect_match: SkincareItem[]
  complete_your_routine: {
    label: string
    steps: RoutineStep[]
  } | null
  frequently_bought_together: SkincareItem[]
  others_with_skin_type_liked: ItemDetail[]
  skin_type_label: string
}

async function fetchSkincareRecs(itemId: string): Promise<SkincareResponse> {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/items/${itemId}/skincare-recommendations`,
  )
  if (!response.ok) throw new Error("Failed to load skincare recommendations")
  return response.json()
}

async function fetchItemReviews(itemId: string): Promise<ReviewsResponse> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/reviews/item/${itemId}?limit=100`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  if (!response.ok) throw new Error("Failed to load reviews")
  return response.json()
}

export const Route = createFileRoute("/_layout/item/$id" as any)({
  component: ItemDetailPage,
  head: () => ({
    meta: [{ title: "Product Details" }],
  }),
})

function ItemDetailPage() {
  const { id } = Route.useParams()
  const navigate = useNavigate()

  const { data: item, isLoading: isItemLoading } = useQuery({
    queryKey: ["item", id],
    queryFn: () => fetchItem(id),
  })

  const { data: reviewsResponse, isLoading: isReviewsLoading } = useQuery({
    queryKey: ["item-reviews", id],
    queryFn: () => fetchItemReviews(id),
    enabled: !!id,
  })

  const { data: similarResponse, isLoading: isSimilarLoading } = useQuery({
    queryKey: ["similar-items", id],
    queryFn: () => fetchSimilarItems(id),
    enabled: !!id,
  })

  const { data: skincareRecs } = useQuery({
    queryKey: ["skincare-recs", id],
    queryFn: () => fetchSkincareRecs(id),
    enabled: !!id,
  })

  if (isItemLoading) {
    return <p className="text-muted-foreground p-4">Loading product...</p>
  }

  if (!item) {
    return <p className="text-destructive p-4">Product not found.</p>
  }

  const reviews = reviewsResponse?.data ?? []

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      {/* Back link */}
      <Link to="/search">
        <Button variant="ghost" size="sm" className="gap-1">
          <ArrowLeft className="size-4" /> Back to Search
        </Button>
      </Link>

      {/* Product Header */}
      <div className="flex flex-col md:flex-row gap-6">
        {/* Image */}
        <div className="w-full md:w-72 shrink-0">
          {item.image_url ? (
            <img
              src={item.image_url}
              alt={item.title}
              className="w-full h-64 object-cover rounded-lg border"
            />
          ) : (
            <div className="w-full h-64 bg-muted rounded-lg border flex items-center justify-center">
              <span className="text-muted-foreground text-sm">No image</span>
            </div>
          )}
        </div>

        {/* Details */}
        <div className="flex-1 space-y-3">
          {item.brand && (
            <p className="text-sm font-medium text-primary uppercase tracking-wide">
              {item.brand}
            </p>
          )}
          <h1 className="text-2xl font-bold">{item.title}</h1>

          {item.description && (
            <p className="text-muted-foreground">{item.description}</p>
          )}

          <div className="flex items-center gap-4">
            {item.product_rating != null && (
              <div className="flex items-center gap-1">
                <Star className="size-4 fill-amber-400 text-amber-400" />
                <span className="font-medium">{item.product_rating.toFixed(1)}</span>
                {item.product_rating_count != null && (
                  <span className="text-sm text-muted-foreground">
                    ({item.product_rating_count} reviews)
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex items-baseline gap-3 pt-2">
            {item.price != null && (
              <span className="text-2xl font-bold">₹{item.price.toFixed(0)}</span>
            )}
            {item.mrp != null && item.price != null && item.mrp > item.price && (
              <span className="text-lg text-muted-foreground line-through">
                ₹{item.mrp.toFixed(0)}
              </span>
            )}
          </div>

          {item.product_url && (
            <a
              href={item.product_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline"
            >
              View on store →
            </a>
          )}
        </div>
      </div>

      {/* ── Skincare Smart Recommendations ─────────────────────── */}

      {/* Detected Tags */}
      {skincareRecs?.item_tags && (
        Object.values(skincareRecs.item_tags).some((arr) => arr.length > 0) && (
          <div className="border-t pt-6">
            <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <FlaskConical className="size-5 text-purple-500" /> Detected Skincare Profile
            </h2>
            <div className="flex flex-wrap gap-2">
              {skincareRecs.item_tags.ingredients.map((t) => (
                <span key={t} className="text-xs px-2 py-1 rounded-full bg-purple-100 text-purple-700 font-medium">
                  {t.replace(/_/g, " ")}
                </span>
              ))}
              {skincareRecs.item_tags.skin_types.map((t) => (
                <span key={t} className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700 font-medium">
                  {t.replace(/_/g, " ")}
                </span>
              ))}
              {skincareRecs.item_tags.concerns.map((t) => (
                <span key={t} className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700 font-medium">
                  {t.replace(/_/g, " ")}
                </span>
              ))}
              {skincareRecs.item_tags.product_steps.map((t) => (
                <span key={t} className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700 font-medium">
                  {t.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        )
      )}

      {/* The Perfect Match — Ingredient Synergy */}
      {skincareRecs?.perfect_match && skincareRecs.perfect_match.length > 0 && (
        <div className="border-t pt-6">
          <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
            <Sparkles className="size-5 text-amber-500" /> The Perfect Match
          </h2>
          <p className="text-xs text-muted-foreground mb-4">
            Ingredients that enhance each other's efficacy — science-backed pairings
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {skincareRecs.perfect_match.map((pm: SkincareItem) => (
              <div
                key={pm.id}
                onClick={() => navigate({ to: "/item/$id", params: { id: pm.id } } as any)}
                className="cursor-pointer rounded-lg border bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 p-4 shadow-sm transition-all hover:shadow-md hover:border-amber-300"
              >
                <div className="flex gap-3">
                  {pm.image_url ? (
                    <img src={pm.image_url} alt={pm.title} className="w-16 h-16 object-cover rounded-md shrink-0" />
                  ) : (
                    <div className="w-16 h-16 bg-muted rounded-md shrink-0 flex items-center justify-center">
                      <span className="text-xs text-muted-foreground">No img</span>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    {pm.brand && (
                      <p className="text-xs font-medium text-primary uppercase tracking-wide">{pm.brand}</p>
                    )}
                    <h3 className="font-medium text-sm line-clamp-2">{pm.title}</h3>
                    {pm.price != null && (
                      <span className="text-xs font-semibold">₹{pm.price.toFixed(0)}</span>
                    )}
                  </div>
                </div>
                {pm.reason && (
                  <p className="mt-2 text-xs text-muted-foreground italic border-t pt-2">
                    {pm.reason}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Complete Your Routine — Skin Type Bundle */}
      {skincareRecs?.complete_your_routine && (
        <div className="border-t pt-6">
          <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
            <ShoppingCart className="size-5 text-emerald-500" /> Complete Your Routine
          </h2>
          <p className="text-sm font-medium text-emerald-600 mb-4">
            {skincareRecs.complete_your_routine.label}
          </p>
          <div className="space-y-4">
            {skincareRecs.complete_your_routine.steps.map((step: RoutineStep) => (
              <div key={step.step}>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Step: {step.step.replace(/_/g, " ")}
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {step.items.map((si: ItemDetail) => (
                    <div
                      key={si.id}
                      onClick={() => navigate({ to: "/item/$id", params: { id: si.id } } as any)}
                      className="cursor-pointer rounded-lg border bg-emerald-50 dark:bg-emerald-950/20 p-3 shadow-sm transition-all hover:shadow-md hover:border-emerald-300"
                    >
                      {si.image_url ? (
                        <img src={si.image_url} alt={si.title} className="w-full h-20 object-cover rounded-md mb-1" />
                      ) : (
                        <div className="w-full h-20 bg-muted rounded-md mb-1 flex items-center justify-center">
                          <span className="text-xs text-muted-foreground">No img</span>
                        </div>
                      )}
                      <h4 className="font-medium text-xs line-clamp-2">{si.title}</h4>
                      {si.price != null && (
                        <span className="text-xs font-semibold">₹{si.price.toFixed(0)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Frequently Bought Together */}
      {skincareRecs?.frequently_bought_together && skincareRecs.frequently_bought_together.length > 0 && (
        <div className="border-t pt-6">
          <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
            <ShoppingCart className="size-5 text-indigo-500" /> Frequently Bought Together
          </h2>
          <p className="text-xs text-muted-foreground mb-4">
            Customers who reviewed this also reviewed these products
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {skincareRecs.frequently_bought_together.map((fbt: SkincareItem) => (
              <div
                key={fbt.id}
                onClick={() => navigate({ to: "/item/$id", params: { id: fbt.id } } as any)}
                className="cursor-pointer rounded-lg border bg-indigo-50 dark:bg-indigo-950/20 p-3 shadow-sm transition-all hover:shadow-md hover:border-indigo-300"
              >
                {fbt.image_url ? (
                  <img src={fbt.image_url} alt={fbt.title} className="w-full h-24 object-cover rounded-md mb-2" />
                ) : (
                  <div className="w-full h-24 bg-muted rounded-md mb-2 flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">No img</span>
                  </div>
                )}
                {fbt.brand && (
                  <p className="text-xs font-medium text-primary uppercase tracking-wide mb-0.5">{fbt.brand}</p>
                )}
                <h3 className="font-medium text-xs line-clamp-2 mb-1">{fbt.title}</h3>
                {fbt.co_purchase_count != null && (
                  <span className="text-xs text-indigo-600 font-medium">
                    {fbt.co_purchase_count} customers bought both
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Others with Skin Type Liked */}
      {skincareRecs?.others_with_skin_type_liked && skincareRecs.others_with_skin_type_liked.length > 0 && (
        <div className="border-t pt-6">
          <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
            <Users className="size-5 text-pink-500" />{" "}
            Others with {skincareRecs.skin_type_label || "Similar"} Skin Liked
          </h2>
          <p className="text-xs text-muted-foreground mb-4">
            Products matching the same skin type profile
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {skincareRecs.others_with_skin_type_liked.map((ot: ItemDetail) => (
              <div
                key={ot.id}
                onClick={() => navigate({ to: "/item/$id", params: { id: ot.id } } as any)}
                className="cursor-pointer rounded-lg border bg-pink-50 dark:bg-pink-950/20 p-3 shadow-sm transition-all hover:shadow-md hover:border-pink-300"
              >
                {ot.image_url ? (
                  <img src={ot.image_url} alt={ot.title} className="w-full h-24 object-cover rounded-md mb-2" />
                ) : (
                  <div className="w-full h-24 bg-muted rounded-md mb-2 flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">No img</span>
                  </div>
                )}
                {ot.brand && (
                  <p className="text-xs font-medium text-primary uppercase tracking-wide mb-0.5">{ot.brand}</p>
                )}
                <h3 className="font-medium text-xs line-clamp-2 mb-1">{ot.title}</h3>
                <div className="flex items-center justify-between">
                  {ot.product_rating != null && (
                    <div className="flex items-center gap-0.5">
                      <Star className="size-3 fill-amber-400 text-amber-400" />
                      <span className="text-xs">{ot.product_rating.toFixed(1)}</span>
                    </div>
                  )}
                  {ot.price != null && (
                    <span className="text-xs font-semibold">₹{ot.price.toFixed(0)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Similar Items Section */}
      <div className="border-t pt-6">
        <h2 className="text-xl font-semibold mb-4">Similar Products</h2>
        <p className="text-xs text-muted-foreground mb-3">
          Recommended using hybrid collaborative filtering + content similarity
        </p>

        {isSimilarLoading && (
          <p className="text-muted-foreground">Loading recommendations...</p>
        )}

        {!isSimilarLoading && (!similarResponse || similarResponse.data.length === 0) && (
          <p className="text-muted-foreground">No similar products found.</p>
        )}

        {similarResponse && similarResponse.data.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {similarResponse.data.map((sim) => (
              <div
                key={sim.id}
                onClick={() => navigate({ to: "/item/$id", params: { id: sim.id } } as any)}
                className="cursor-pointer rounded-lg border bg-card p-3 shadow-sm transition-all hover:shadow-md hover:border-primary/50"
              >
                {sim.image_url ? (
                  <img
                    src={sim.image_url}
                    alt={sim.title}
                    className="w-full h-28 object-cover rounded-md mb-2"
                  />
                ) : (
                  <div className="w-full h-28 bg-muted rounded-md mb-2 flex items-center justify-center">
                    <span className="text-muted-foreground text-xs">No image</span>
                  </div>
                )}
                {sim.brand && (
                  <p className="text-xs font-medium text-primary uppercase tracking-wide mb-0.5">
                    {sim.brand}
                  </p>
                )}
                <h3 className="font-medium text-xs line-clamp-2 mb-1">{sim.title}</h3>
                <div className="flex items-center justify-between">
                  {sim.product_rating != null && (
                    <div className="flex items-center gap-0.5">
                      <Star className="size-3 fill-amber-400 text-amber-400" />
                      <span className="text-xs">{sim.product_rating.toFixed(1)}</span>
                    </div>
                  )}
                  {sim.price != null && (
                    <span className="text-xs font-semibold">₹{sim.price.toFixed(0)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reviews Section */}
      <div className="border-t pt-6">
        <h2 className="text-xl font-semibold mb-4">
          Reviews {reviewsResponse && `(${reviewsResponse.count})`}
        </h2>

        {isReviewsLoading && (
          <p className="text-muted-foreground">Loading reviews...</p>
        )}

        {!isReviewsLoading && reviews.length === 0 && (
          <p className="text-muted-foreground">No reviews yet for this product.</p>
        )}

        <div className="space-y-4">
          {reviews.map((review) => (
            <div key={review.id} className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star
                        key={s}
                        className={`size-3.5 ${
                          s <= review.rating
                            ? "fill-amber-400 text-amber-400"
                            : "text-muted-foreground"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="font-medium text-sm">{review.title}</span>
                </div>
                {review.is_a_buyer != null && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      review.is_a_buyer
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {review.is_a_buyer ? "Verified Buyer" : "Non-Buyer"}
                  </span>
                )}
              </div>

              <p className="text-sm text-muted-foreground">{review.description}</p>

              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <User className="size-3" />
                  {review.owner_name || "Anonymous"}
                </span>
                {review.review_date && (
                  <span>{new Date(review.review_date).toLocaleDateString()}</span>
                )}
                {review.predicted_is_a_buyer != null && (
                  <span className="italic">
                    AI predicted: {review.predicted_is_a_buyer ? "Buyer" : "Non-Buyer"}
                    {review.prediction_confidence != null &&
                      ` (${(review.prediction_confidence * 100).toFixed(0)}%)`}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
