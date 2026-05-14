import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { type ItemPublic, ItemsService } from "@/client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { LoadingButton } from "@/components/ui/loading-button";
import useCustomToast from "@/hooks/useCustomToast";
import { handleError } from "@/utils";

const formSchema = z.object({
	title: z.string().min(1, { message: "Title is required" }),
	description: z.string().optional(),
	image_url: z.string().url({ message: "Must be a valid URL" }).optional(),
	brand: z.string().optional(),
	price: z.number().nonnegative().optional(),
	mrp: z.number().nonnegative().optional(),
	product_id: z.number().nonnegative().optional(),
	product_url: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

interface EditItemProps {
	item: ItemPublic & {
		image_url?: string | null;
		brand?: string | null;
		price?: number | null;
		mrp?: number | null;
	};
	onSuccess: () => void;
}

const EditItem = ({ item, onSuccess }: EditItemProps) => {
	const [isOpen, setIsOpen] = useState(false);
	const queryClient = useQueryClient();
	const { showSuccessToast, showErrorToast } = useCustomToast();

	const form = useForm<FormData>({
		resolver: zodResolver(formSchema),
		mode: "onBlur",
		criteriaMode: "all",
		defaultValues: {
			title: item.title,
			description: item.description ?? undefined,
			image_url: item.image_url ?? undefined,
			brand: item.brand ?? undefined,
			price: item.price ?? undefined,
			mrp: item.mrp ?? undefined,
			product_id: item.product_id ?? undefined,
			product_url: item.product_url ?? undefined,
		},
	});

	const mutation = useMutation({
		mutationFn: (data: FormData) => ItemsService.updateItem({ id: item.id, requestBody: data }),
		onSuccess: () => {
			showSuccessToast("Item updated successfully");
			setIsOpen(false);
			onSuccess();
		},
		onError: handleError.bind(showErrorToast),
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: ["items"] });
		},
	});

	const onSubmit = (data: FormData) => {
		mutation.mutate({
			...data,
			description: data.description?.trim() ? data.description : undefined,
			brand: data.brand?.trim() ? data.brand : undefined,
			product_url: data.product_url?.trim() ? data.product_url : undefined,
			image_url: data.image_url?.trim() ? data.image_url : undefined,
		} as FormData);
	};

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<DropdownMenuItem onSelect={(e) => e.preventDefault()} onClick={() => setIsOpen(true)}>
				<Pencil />
				Edit Item
			</DropdownMenuItem>
			<DialogContent className="sm:max-w-md">
				<Form {...form}>
					<form onSubmit={form.handleSubmit(onSubmit)}>
						<DialogHeader>
							<DialogTitle>Edit Item</DialogTitle>
							<DialogDescription>Update the item details below.</DialogDescription>
						</DialogHeader>
						<div className="grid gap-4 py-4">
							<FormField
								control={form.control}
								name="title"
								render={({ field }) => (
									<FormItem>
										<FormLabel>
											Title <span className="text-destructive">*</span>
										</FormLabel>
										<FormControl>
											<Input placeholder="Title" type="text" {...field} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="description"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Description</FormLabel>
										<FormControl>
											<Input placeholder="Description" type="text" {...field} value={field.value ?? ""} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="product_id"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Product ID</FormLabel>
										<FormControl>
											<Input
												placeholder="e.g. 1001"
												type="number"
												step="1"
												min="0"
												value={field.value ?? ""}
												onChange={(e) => field.onChange(e.target.value === "" ? undefined : Number(e.target.value))}
												onBlur={field.onBlur}
												name={field.name}
												ref={field.ref}
											/>
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="price"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Price</FormLabel>
										<FormControl>
											<Input
												placeholder="Price"
												type="number"
												min="0"
												step="0.01"
												value={field.value ?? ""}
												onChange={(e) => field.onChange(e.target.value === "" ? undefined : Number(e.target.value))}
												onBlur={field.onBlur}
												name={field.name}
												ref={field.ref}
											/>
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="mrp"
								render={({ field }) => (
									<FormItem>
										<FormLabel>MRP</FormLabel>
										<FormControl>
											<Input
												placeholder="MRP"
												type="number"
												min="0"
												step="0.01"
												value={field.value ?? ""}
												onChange={(e) => field.onChange(e.target.value === "" ? undefined : Number(e.target.value))}
												onBlur={field.onBlur}
												name={field.name}
												ref={field.ref}
											/>
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="brand"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Brand</FormLabel>
										<FormControl>
											<Input placeholder="Brand" type="text" {...field} value={field.value ?? ""} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="product_url"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Product URL</FormLabel>
										<FormControl>
											<Input placeholder="https://example.com/product" type="text" {...field} value={field.value ?? ""} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="image_url"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Image URL</FormLabel>
										<FormControl>
											<Input placeholder="https://example.com/image.jpg" type="text" {...field} value={field.value ?? ""} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="image_url"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Image URL</FormLabel>
										<FormControl>
											<Input placeholder="https://example.com/image.jpg" type="url" {...field} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="brand"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Brand</FormLabel>
										<FormControl>
											<Input placeholder="Brand" type="text" {...field} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="price"
								render={({ field }) => (
									<FormItem>
										<FormLabel>Price</FormLabel>
										<FormControl>
											<Input placeholder="0.00" type="number" step="0.01" {...field} onChange={(e) => field.onChange(e.target.valueAsNumber)} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>

							<FormField
								control={form.control}
								name="mrp"
								render={({ field }) => (
									<FormItem>
										<FormLabel>MRP</FormLabel>
										<FormControl>
											<Input placeholder="0.00" type="number" step="0.01" {...field} onChange={(e) => field.onChange(e.target.valueAsNumber)} />
										</FormControl>
										<FormMessage />
									</FormItem>
								)}
							/>
						</div>

						<DialogFooter>
							<DialogClose asChild>
								<Button variant="outline" disabled={mutation.isPending}>
									Cancel
								</Button>
							</DialogClose>
							<LoadingButton type="submit" loading={mutation.isPending}>
								Save
							</LoadingButton>
						</DialogFooter>
					</form>
				</Form>
			</DialogContent>
		</Dialog>
	);
};

export default EditItem;
