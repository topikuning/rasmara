import { redirect } from "next/navigation";

export default async function ContractIndex({
  params,
}: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/kontrak/${id}/ringkasan`);
}
