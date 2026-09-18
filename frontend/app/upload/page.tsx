import { DocumentUpload } from "@/components/upload/DocumentUpload";

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Document upload
        </h1>
        <p className="text-sm text-muted-foreground">
          Upload a government document image and verify the extracted fields.
        </p>
      </div>
      <DocumentUpload />
    </div>
  );
}
