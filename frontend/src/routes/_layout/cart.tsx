import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { Minus, Plus, ShoppingCart, Sparkles, Trash2, X } from "lucide-react"
import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Dialog, DialogClose, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog"
import { useState } from "react"
import useCustomToast from "@/hooks/useCustomToast"

type CartItem = {
  id: string
  item_id: string
  quantity: number
  title: string
  brand?: string | null
  image_url?: string | null
  price?: number | null
  mrp?: number | null
}

type CartPublic = { items: CartItem[]; total: number }

type PerfectMatchItem = {
  id: string
  title: string
  brand?: string | null
  image_url?: string | null
  price?: number | null
  mrp?: number | null
  reason?: string
  synergy_ingredient?: string
}

type CartRecsResponse = { perfect_match: PerfectMatchItem[] }

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`, "Content-Type": "application/json" }
}

async function fetchCart(): Promise<CartPublic> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/`, { headers: authHeaders() })
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

async function updateQty(item_id: string, quantity: number): Promise<CartPublic> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/${item_id}?quantity=${quantity}`, { method: "PATCH", headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to update quantity")
  return res.json()
}

async function removeItem(item_id: string): Promise<CartPublic> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/${item_id}`, { method: "DELETE", headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to remove item")
  return res.json()
}

async function clearCart(): Promise<void> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/clear`, { method: "DELETE", headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to clear cart")
}

async function fetchCartRecs(): Promise<CartRecsResponse> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/recommendations`, { headers: authHeaders() })
  if (!res.ok) return { perfect_match: [] }
  return res.json()
}

async function addItemToCart(itemId: string): Promise<CartPublic> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/${itemId}?quantity=1`, { method: "POST", headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to add to cart")
  return res.json()
}

export const Route = createFileRoute("/_layout/cart")({
  component: CartPage,
  head: () => ({ meta: [{ title: "Cart" }] }),
})

function CartPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [clearOpen, setClearOpen] = useState(false)

  const { data: cart, isLoading } = useQuery({ queryKey: ["cart"], queryFn: fetchCart })

  const items = cart?.items ?? []

  const { data: cartRecs } = useQuery({
    queryKey: ["cart-recommendations"],
    queryFn: fetchCartRecs,
    enabled: items.length > 0,
  })

  const addRecMutation = useMutation({
    mutationFn: (itemId: string) => addItemToCart(itemId),
    onSuccess: (data) => {
      queryClient.setQueryData(["cart"], data)
      queryClient.invalidateQueries({ queryKey: ["cart-recommendations"] })
      showSuccessToast("Added to cart")
    },
    onError: (e: Error) => showErrorToast(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ item_id, quantity }: { item_id: string; quantity: number }) => updateQty(item_id, quantity),
    onSuccess: (data) => { queryClient.setQueryData(["cart"], data) },
    onError: (e: Error) => showErrorToast(e.message),
  })

  const removeMutation = useMutation({
    mutationFn: (item_id: string) => removeItem(item_id),
    onSuccess: (data) => { queryClient.setQueryData(["cart"], data); showSuccessToast("Item removed") },
    onError: (e: Error) => showErrorToast(e.message),
  })

  const clearMutation = useMutation({
    mutationFn: clearCart,
    onSuccess: () => {
      queryClient.setQueryData(["cart"], { items: [], total: 0 })
      queryClient.invalidateQueries({ queryKey: ["cart-recommendations"] })
      setClearOpen(false)
      showSuccessToast("Cart cleared")
    },
    onError: (e: Error) => showErrorToast(e.message),
  })
  const total = cart?.total ?? 0

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cart</h1>
          <p className="text-muted-foreground">{items.length === 0 ? "Your cart is empty" : `${items.reduce((s, i) => s + i.quantity, 0)} item(s)`}</p>
        </div>
        {items.length > 0 && (
          <Dialog open={clearOpen} onOpenChange={setClearOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm"><X className="size-4 mr-1" />Clear cart</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Clear Cart</DialogTitle>
                <DialogDescription>Remove all items from your cart?</DialogDescription>
              </DialogHeader>
              <DialogFooter className="mt-4">
                <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
                <LoadingButton variant="destructive" loading={clearMutation.isPending} onClick={() => clearMutation.mutate()}>Clear</LoadingButton>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {isLoading && <p className="text-muted-foreground">Loading cart...</p>}

      {!isLoading && items.length === 0 && (
        <div className="flex flex-col items-center justify-center text-center py-16 gap-4">
          <div className="rounded-full bg-muted p-4">
            <ShoppingCart className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No items in your cart</h3>
          <p className="text-muted-foreground">Browse products and add them to your cart.</p>
          <Link to="/search"><Button>Browse Products</Button></Link>
        </div>
      )}

      {items.length > 0 && (
        <div className="flex flex-col gap-4">
          {items.map((item) => (
            <div key={item.id} className="flex gap-4 rounded-lg border p-4 items-center">
              {item.image_url ? (
                <img src={item.image_url} alt={item.title} className="w-20 h-20 object-cover rounded-md shrink-0" />
              ) : (
                <div className="w-20 h-20 bg-muted rounded-md shrink-0 flex items-center justify-center">
                  <ShoppingCart className="size-6 text-muted-foreground" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                {item.brand && <p className="text-xs font-medium text-primary uppercase tracking-wide">{item.brand}</p>}
                <Link to="/item/$id" params={{ id: item.item_id } as any}>
                  <h3 className="font-semibold text-sm hover:underline line-clamp-2">{item.title}</h3>
                </Link>
                <div className="flex items-baseline gap-2 mt-1">
                  {item.price != null && <span className="font-bold">₹{item.price.toFixed(0)}</span>}
                  {item.mrp != null && item.price != null && item.mrp > item.price && (
                    <span className="text-xs text-muted-foreground line-through">₹{item.mrp.toFixed(0)}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button variant="outline" size="icon" className="h-7 w-7"
                  disabled={item.quantity <= 1 || updateMutation.isPending}
                  onClick={() => updateMutation.mutate({ item_id: item.item_id, quantity: item.quantity - 1 })}>
                  <Minus className="size-3" />
                </Button>
                <span className="w-6 text-center text-sm font-medium">{item.quantity}</span>
                <Button variant="outline" size="icon" className="h-7 w-7"
                  disabled={updateMutation.isPending}
                  onClick={() => updateMutation.mutate({ item_id: item.item_id, quantity: item.quantity + 1 })}>
                  <Plus className="size-3" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                  disabled={removeMutation.isPending}
                  onClick={() => removeMutation.mutate(item.item_id)}>
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </div>
          ))}

          <div className="rounded-lg border p-4 bg-muted/30 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">₹{total.toFixed(0)}</p>
            </div>
            <Button size="lg">Checkout</Button>
          </div>
        </div>
      )}

      {/* Perfect Match Recommendations */}
      {cartRecs?.perfect_match && cartRecs.perfect_match.length > 0 && (
        <div className="border-t pt-6">
          <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
            <Sparkles className="size-5 text-amber-500" /> The Perfect Match
          </h2>
          <p className="text-xs text-muted-foreground mb-4">
            Based on items in your cart — science-backed ingredient pairings you might love
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {cartRecs.perfect_match.map((pm) => (
              <div
                key={pm.id}
                className="rounded-lg border bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 p-4 shadow-sm transition-all hover:shadow-md hover:border-amber-300"
              >
                <div
                  className="flex gap-3 cursor-pointer"
                  onClick={() => navigate({ to: "/item/$id", params: { id: pm.id } } as any)}
                >
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
                      <div className="flex items-baseline gap-2 mt-0.5">
                        <span className="text-xs font-semibold">₹{pm.price.toFixed(0)}</span>
                        {pm.mrp != null && pm.mrp > pm.price && (
                          <span className="text-xs text-muted-foreground line-through">₹{pm.mrp.toFixed(0)}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                {pm.reason && (
                  <p className="mt-2 text-xs text-muted-foreground italic border-t pt-2">
                    {pm.reason}
                  </p>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-2 w-full text-xs"
                  disabled={addRecMutation.isPending}
                  onClick={() => addRecMutation.mutate(pm.id)}
                >
                  <Plus className="size-3 mr-1" /> Add to Cart
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
