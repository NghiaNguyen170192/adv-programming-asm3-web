import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { EllipsisVertical, Pencil, Trash2 } from "lucide-react"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { Button } from "@/components/ui/button"
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
import useCustomToast from "@/hooks/useCustomToast"

type TagPublicRow = {
  id: string
  name: string
}

const columns: ColumnDef<TagPublicRow>[] = [
  { accessorKey: "name", header: "Name" },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <TagActionsCell row={row.original} />,
  },
]

export const Route = createFileRoute("/_layout/tags")({
  component: Tags,
  head: () => ({
    meta: [
      {
        title: "Tags - FastAPI Template",
      },
    ],
  }),
})

async function readTags(
  skip: number = 0,
  limit: number = 25,
): Promise<TagPublicRow[]> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/tags/?skip=${skip}&limit=${limit}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!response.ok) {
    throw new Error("Failed to load tags")
  }

  return response.json()
}

async function createTag(name: string): Promise<TagPublicRow> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}/api/v1/tags/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || "Failed to create tag")
  }

  return response.json()
}

async function updateTag(tagId: string, name: string): Promise<TagPublicRow> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}/api/v1/tags/${tagId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  })
  if (!response.ok)
    throw new Error((await response.text()) || "Failed to update tag")
  return response.json()
}

async function deleteTag(tagId: string): Promise<void> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(`${OpenAPI.BASE}/api/v1/tags/${tagId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok)
    throw new Error((await response.text()) || "Failed to delete tag")
}

// ─── Actions cell ─────────────────────────────────────────────────────────────

function TagActionsCell({ row }: { row: TagPublicRow }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [editName, setEditName] = useState(row.name)

  const editMutation = useMutation({
    mutationFn: () => updateTag(row.id, editName.trim()),
    onSuccess: () => {
      showSuccessToast("Tag updated successfully")
      setIsEditOpen(false)
      setMenuOpen(false)
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (e: Error) => showErrorToast(e.message || "Failed to update tag"),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteTag(row.id),
    onSuccess: () => {
      showSuccessToast("Tag deleted successfully")
      setIsDeleteOpen(false)
      setMenuOpen(false)
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (e: Error) => showErrorToast(e.message || "Failed to delete tag"),
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
            <Pencil className="size-4" /> Edit Tag
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onSelect={(e) => {
              e.preventDefault()
              setIsDeleteOpen(true)
            }}
          >
            <Trash2 className="size-4" /> Delete Tag
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Edit dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Tag</DialogTitle>
            <DialogDescription>Update the tag name.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2 py-2">
            <Label htmlFor="edit-tag-name">Tag Name</Label>
            <Input
              id="edit-tag-name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
            />
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
              disabled={!editName.trim()}
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
            <DialogTitle>Delete Tag</DialogTitle>
            <DialogDescription>
              This tag will be permanently deleted. Are you sure?
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

function Tags() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [currentPage, setCurrentPage] = useState(0)
  const pageSize = 25
  const { data: tags = [], isLoading } = useQuery({
    queryKey: ["tags", currentPage],
    queryFn: () => readTags(currentPage * pageSize, pageSize),
  })
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [tagName, setTagName] = useState("")

  const createMutation = useMutation({
    mutationFn: () => createTag(tagName.trim()),
    onSuccess: () => {
      showSuccessToast("Tag created successfully")
      setIsCreateOpen(false)
      setTagName("")
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (error) => {
      showErrorToast(error.message || "Failed to create tag")
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tags</h1>
          <p className="text-muted-foreground">
            Display and create tags from backend model.
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>Create Tag</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Tag</DialogTitle>
              <DialogDescription>Create a new tag name.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-2 py-2">
              <Label htmlFor="tag-name">Tag Name</Label>
              <Input
                id="tag-name"
                value={tagName}
                onChange={(e) => setTagName(e.target.value)}
                placeholder="e.g. skincare"
              />
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
                disabled={!tagName.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : (
        <DataTable
          columns={columns}
          data={tags}
          showPagination
          totalCount={Math.max(tags.length, (currentPage + 1) * pageSize)}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
        />
      )}
    </div>
  )
}
