import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { EllipsisVertical, Pencil, Trash2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { type ItemPublic, OpenAPI } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"

type ReviewPublicRow = {
  id: string
  review_id?: string | null
  title: string
  item_id: string
  rating: number
  review_date?: string | null
  is_a_buyer?: boolean | null
  predicted_is_a_buyer?: boolean | null
  prediction_confidence?: number | null
  review_label?: string | null
  owner_id: string
  owner_name?: string | null
  description: string
  item_title?: string | null
  created_at?: string | null
}

type PredictResponse = {
  predicted_is_buyer: boolean
  confidence: number
  model_probabilities: {
    bow_rf: number
    bow_lr: number
    ft_lr: number
  }
  fusion_method: string
}

type ReviewsPublicResponse = {
  data: ReviewPublicRow[]
  count: number
}

const REVIEWS_PER_PAGE = 50

// ─── API helpers ─────────────────────────────────────────────────────────────

async function readItems(
  skip: number = 0,
  limit: number = 100,
): Promise<ItemPublic[]> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/items/?skip=${skip}&limit=${limit}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  )
  if (!response.ok) throw new Error("Failed to load items")
  const data = await response.json()
  return data.data || []
}

async function readReviews(
  skip: number = 0,
  limit: number = REVIEWS_PER_PAGE,
): Promise<ReviewsPublicResponse> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/reviews/?skip=${skip}&limit=${limit}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  )
  if (!response.ok) throw new Error("Failed to load reviews")
  return response.json()
}

type CreateReviewPayload = {
  title: string
  description: string
  rating: number
  item_id: string
  is_a_buyer?: boolean
  review_label?: string
}

async function predictBuyer(
  reviewText: string,
): Promise<PredictResponse> {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/predict/`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review_text: reviewText }),
    },
  )
  if (!response.ok) throw new Error("Prediction failed")
  return response.json()
}

async function createReview(
  itemId: string,
  payload: CreateReviewPayload,
): Promise<ReviewPublicRow> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/reviews/item/${itemId}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  )
  if (!response.ok)
    throw new Error((await response.text()) || "Failed to create review")
  return response.json()
}

async function updateReview(
  reviewId: string,
  data: { title: string; description: string; rating: number },
): Promise<ReviewPublicRow> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}/api/v1/reviews/${reviewId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  })
  if (!response.ok)
    throw new Error((await response.text()) || "Failed to update review")
  return response.json()
}

async function deleteReview(reviewId: string): Promise<void> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}/api/v1/reviews/${reviewId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok)
    throw new Error((await response.text()) || "Failed to delete review")
}

// ─── Actions cell ─────────────────────────────────────────────────────────────

function ReviewActionsCell({ row }: { row: ReviewPublicRow }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [editTitle, setEditTitle] = useState(row.title)
  const [editDescription, setEditDescription] = useState(row.description)
  const [editRating, setEditRating] = useState(String(row.rating))

  const reviewId = row.review_id ?? row.id

  const editMutation = useMutation({
    mutationFn: () =>
      updateReview(reviewId, {
        title: editTitle.trim(),
        description: editDescription.trim(),
        rating: Number(editRating),
      }),
    onSuccess: () => {
      showSuccessToast("Review updated successfully")
      setIsEditOpen(false)
      setMenuOpen(false)
      queryClient.invalidateQueries({ queryKey: ["reviews"] })
    },
    onError: (e: Error) =>
      showErrorToast(e.message || "Failed to update review"),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteReview(reviewId),
    onSuccess: () => {
      showSuccessToast("Review deleted successfully")
      setIsDeleteOpen(false)
      setMenuOpen(false)
      queryClient.invalidateQueries({ queryKey: ["reviews"] })
    },
    onError: (e: Error) =>
      showErrorToast(e.message || "Failed to delete review"),
  })

  return (
    <div className="flex justify-end">
      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon">
            <EllipsisVertical className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault()
              setIsEditOpen(true)
            }}
          >
            <Pencil className="size-4" /> Edit Review
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onSelect={(e) => {
              e.preventDefault()
              setIsDeleteOpen(true)
            }}
          >
            <Trash2 className="size-4" /> Delete Review
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Edit dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Review</DialogTitle>
            <DialogDescription>
              Update title, description and rating.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <div className="grid gap-1">
              <Label htmlFor="edit-review-title">Title</Label>
              <Input
                id="edit-review-title"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="edit-review-description">Description</Label>
              <Input
                id="edit-review-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="edit-review-rating">Rating (1–5)</Label>
              <Input
                id="edit-review-rating"
                type="number"
                min="1"
                max="5"
                step="1"
                value={editRating}
                onChange={(e) => setEditRating(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={editMutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              loading={editMutation.isPending}
              onClick={() => editMutation.mutate()}
              disabled={!editTitle.trim() || !editDescription.trim()}
            >
              Save
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete dialog */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Review</DialogTitle>
            <DialogDescription>
              This review will be permanently deleted. Are you sure?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={deleteMutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Columns ──────────────────────────────────────────────────────────────────

const columns: ColumnDef<ReviewPublicRow>[] = [
  { accessorKey: "title", header: "Title" },
  {
    accessorKey: "item_id",
    header: "Item",
    cell: ({ row }) => row.original.item_title || row.original.item_id,
  },
  { accessorKey: "rating", header: "Rating" },
  {
    accessorKey: "owner_id",
    header: "Author",
    cell: ({ row }) => row.original.owner_name || row.original.owner_id,
  },
  {
    accessorKey: "is_a_buyer",
    header: "Buyer",
    cell: ({ row }) => {
      const value = row.original.is_a_buyer
      if (value == null) return "—"
      return value ? "Yes" : "No"
    },
  },
  {
    accessorKey: "review_label",
    header: "Review Label",
    cell: ({ row }) => row.original.review_label || "—",
  },
  {
    accessorKey: "review_date",
    header: "Review Date",
    cell: ({ row }) =>
      row.original.review_date
        ? new Date(row.original.review_date).toLocaleDateString()
        : "—",
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <div className="max-w-md whitespace-normal wrap-break-word leading-snug">
        {row.original.description}
      </div>
    ),
  },

  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => (
      <div className="min-w-24 whitespace-nowrap">
        {row.original.created_at
          ? new Date(row.original.created_at).toLocaleDateString()
          : "—"}
      </div>
    ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <ReviewActionsCell row={row.original} />,
  },
]

export const Route = createFileRoute("/_layout/reviews")({
  component: Reviews,
  head: () => ({
    meta: [
      {
        title: "Reviews - FastAPI Template",
      },
    ],
  }),
})

function Reviews() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: itemsResponse, isLoading: isItemsLoading } = useQuery({
    queryKey: ["items-for-reviews"],
    queryFn: () => readItems(0, 100),
  })

  const items = useMemo(
    () => (itemsResponse ?? []) as ItemPublic[],
    [itemsResponse],
  )
  const [createItemId, setCreateItemId] = useState<string>("")

  useEffect(() => {
    if (!createItemId && items.length > 0) {
      setCreateItemId(items[0].id)
    }
  }, [items, createItemId])

  const { data: reviewsResponse, isLoading: isReviewsLoading } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => readReviews(0, REVIEWS_PER_PAGE),
  })

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [rating, setRating] = useState("5")
  const [reviewLabel, setReviewLabel] = useState("")
  const [isBuyer, setIsBuyer] = useState<boolean | null>(null)
  const [prediction, setPrediction] = useState<PredictResponse | null>(null)
  const [isPredicting, setIsPredicting] = useState(false)
  const [userOverrode, setUserOverrode] = useState(false)

  const createMutation = useMutation({
    mutationFn: () =>
      createReview(createItemId, {
        title: title.trim(),
        description: description.trim(),
        rating: Number(rating),
        item_id: createItemId,
        review_label: reviewLabel.trim() || undefined,
        is_a_buyer: isBuyer ?? undefined,
      }),
    onSuccess: () => {
      showSuccessToast("Review created successfully")
      setIsCreateOpen(false)
      setTitle("")
      setDescription("")
      setRating("5")
      setReviewLabel("")
      setIsBuyer(null)
      setPrediction(null)
      setUserOverrode(false)
      queryClient.invalidateQueries({ queryKey: ["reviews"] })
    },
    onError: (error) => {
      showErrorToast(error.message || "ailed to create review")
    },
  })

  const canCreateReview = Boolean(
    createItemId && title.trim() && description.trim(),
  )

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">Reviews</h1>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button disabled={!createItemId}>Create Review</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Review</DialogTitle>
              <DialogDescription>
                Create a review and choose which item it belongs to.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="grid gap-2">
                <Label htmlFor="review-item">Item</Label>
                <Select value={createItemId} onValueChange={setCreateItemId}>
                  <SelectTrigger id="review-item">
                    <SelectValue placeholder="Select item" />
                  </SelectTrigger>
                  <SelectContent>
                    {items.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="review-title">Title</Label>
                <Input
                  id="review-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Review title"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="review-description">Description</Label>
                <Input
                  id="review-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Review description"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="review-rating">Rating (1-5)</Label>
                <Input
                  id="review-rating"
                  type="number"
                  min="1"
                  max="5"
                  step="1"
                  value={rating}
                  onChange={(e) => setRating(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="review-label">Review Label</Label>
                <Input
                  id="review-label"
                  value={reviewLabel}
                  onChange={(e) => setReviewLabel(e.target.value)}
                  placeholder="e.g. positive"
                />
              </div>
              {/* ML Prediction Section */}
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-semibold">Buyer Prediction (AI)</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={!description.trim() || isPredicting}
                    onClick={async () => {
                      setIsPredicting(true)
                      try {
                        const result = await predictBuyer(description.trim())
                        setPrediction(result)
                        setIsBuyer(result.predicted_is_buyer)
                        setUserOverrode(false)
                      } catch {
                        showErrorToast("Prediction failed")
                      } finally {
                        setIsPredicting(false)
                      }
                    }}
                  >
                    {isPredicting ? "Predicting..." : prediction ? "Re-predict" : "Predict"}
                  </Button>
                </div>

                {prediction && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          prediction.predicted_is_buyer
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {prediction.predicted_is_buyer ? "Likely Buyer" : "Likely Non-Buyer"}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        Confidence: {(prediction.confidence * 100).toFixed(1)}%
                      </span>
                    </div>

                    <details className="text-xs text-muted-foreground">
                      <summary className="cursor-pointer">Model details</summary>
                      <div className="mt-1 space-y-0.5 pl-2">
                        <div>BoW + Random Forest: {(prediction.model_probabilities.bow_rf * 100).toFixed(1)}%</div>
                        <div>BoW + Logistic Regression: {(prediction.model_probabilities.bow_lr * 100).toFixed(1)}%</div>
                        <div>FastText + Logistic Regression: {(prediction.model_probabilities.ft_lr * 100).toFixed(1)}%</div>
                        <div className="italic">Fusion: soft voting (average)</div>
                      </div>
                    </details>

                    <div className="flex items-center gap-2 pt-1">
                      <Checkbox
                        id="review-buyer-override"
                        checked={isBuyer ?? false}
                        onCheckedChange={(checked) => {
                          setIsBuyer(Boolean(checked))
                          setUserOverrode(Boolean(checked) !== prediction.predicted_is_buyer)
                        }}
                      />
                      <Label htmlFor="review-buyer-override" className="text-sm">
                        Is a buyer
                        {userOverrode && (
                          <span className="ml-1 text-xs text-amber-600">(overridden)</span>
                        )}
                      </Label>
                    </div>
                  </div>
                )}

                {!prediction && (
                  <p className="text-xs text-muted-foreground">
                    Write a review description, then click Predict to get an AI-powered buyer prediction.
                  </p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
                disabled={createMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={() => createMutation.mutate()}
                disabled={!canCreateReview || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      <p className="text-muted-foreground">
        Display and create reviews from backend model.
      </p>

      {isItemsLoading || isReviewsLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : (
        <DataTable
          columns={columns}
          data={reviewsResponse?.data ?? []}
        />
      )}
    </div>
  )
}
