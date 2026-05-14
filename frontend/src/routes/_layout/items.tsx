import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { MoreVertical, Package, Plus, Search, Star } from "lucide-react"

import { ItemsService, OpenAPI } from "@/client"
import AddItem from "@/components/Items/AddItem"
import EditItem from "@/components/Items/EditItem"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useCustomToast from "@/hooks/useCustomToast"

type ItemData = {
  id: string
  title: string
  brand?: string | null
  image_url?: string | null
  price?: number | null
  mrp?: number | null
  product_rating?: number | null
  product_rating_count?: number | null
  description?: string | null
  owner_id: string
}

function authHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
    "Content-Type": "application/json",
  }
}

async function addToCart(itemId: string): Promise<void> {
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/${itemId}?quantity=1`, {
    method: "POST",
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error("Failed to add to cart")
}

type ItemsSearchParams = {
  page: number
}

export const Route = createFileRoute("/_layout/items")({
  component: Items,
  validateSearch: (search: Record<string, unknown>): ItemsSearchParams => ({
    page: typeof search.page === "number" ? search.page : 0,
  }),
  head: () => ({
    meta: [{ title: "Items" }],
  }),
})

function Items() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: items, isLoading } = useQuery({
    queryKey: ["items"],
    queryFn: () => ItemsService.readItems({ skip: 0, limit: 300 }),
  })

  const cartMutation = useMutation({
    mutationFn: addToCart,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] })
      showSuccessToast("Added to cart")
    },
    onError: (e: Error) => showErrorToast(e.message),
  })

  const itemList = (items?.data ?? []) as ItemData[]

  return (
    <div className="flex flex-col gap-6 pb-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-light tracking-tight">All Products</h1>
          <p className="text-muted-foreground">
            {itemList.length === 0 ? "Create and manage your items" : `${itemList.length} product(s)`}
          </p>
        </div>
        <AddItem />
      </div>

      {isLoading && (
        <p className="text-muted-foreground text-sm">Loading items...</p>
      )}

      {!isLoading && itemList.length === 0 && (
        <div className="flex flex-col items-center justify-center text-center py-12">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Search className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">You don't have any items yet</h3>
          <p className="text-muted-foreground">Add a new item to get started</p>
        </div>
      )}

      {itemList.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
          {itemList.map((item) => (
            <div
              key={item.id}
              className="group rounded-none border-0 border-b bg-card transition-all hover:opacity-80 flex flex-col"
            >
              <div className="p-3 flex-1">
                <div className="flex justify-end mb-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <EditItem
                        item={item}
                        onSuccess={() => queryClient.invalidateQueries({ queryKey: ["items"] })}
                      />
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div
                  className="cursor-pointer"
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
                  {item.mrp != null && item.price != null && item.mrp > item.price && (
                    <span className="text-xs text-muted-foreground line-through">₹{item.mrp.toFixed(0)}</span>
                  )}
                </div>
                {item.product_rating != null && item.product_rating > 0 && (
                  <div className="flex items-center gap-1 mt-1">
                    <Star className="size-3 fill-foreground text-foreground" />
                    <span className="text-[10px] text-muted-foreground">
                      {item.product_rating.toFixed(1)}
                      {item.product_rating_count != null && item.product_rating_count > 0 && (
                        <> ({item.product_rating_count})</>
                      )}
                    </span>
                  </div>
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
      )}
    </div>
  )
}