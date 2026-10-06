import { StepProgress } from "@/components/civic/StepProgress";
import { DocumentUpload } from "@/components/upload/DocumentUpload";

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <StepProgress current={2} />
      <DocumentUpload />
    </div>
  );
}
