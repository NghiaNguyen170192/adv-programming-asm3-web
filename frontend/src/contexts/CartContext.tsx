import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createContext, useContext, type ReactNode } from "react"
import { OpenAPI } from "@/client"

type CartPublic = {
  items: { id: string; item_id: string; quantity: number; title: string; price?: number | null; image_url?: string | null; brand?: string | null; mrp?: number | null }[]
  total: number
}

async function fetchCart(): Promise<CartPublic> {
  const token = localStorage.getItem("access_token") || ""
  const res = await fetch(`${OpenAPI.BASE}/api/v1/cart/`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

type CartContextValue = {
  cart: CartPublic | undefined
  itemCount: number
  invalidateCart: () => void
}

const CartContext = createContext<CartContextValue>({
  cart: undefined,
  itemCount: 0,
  invalidateCart: () => {},
})

export function CartProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { data: cart } = useQuery({ queryKey: ["cart"], queryFn: fetchCart })

  const itemCount = cart?.items.reduce((sum, i) => sum + i.quantity, 0) ?? 0
  const invalidateCart = () => queryClient.invalidateQueries({ queryKey: ["cart"] })

  return (
    <CartContext.Provider value={{ cart, itemCount, invalidateCart }}>
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  return useContext(CartContext)
}
