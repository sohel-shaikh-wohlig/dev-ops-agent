import { TerraformForm } from "../components/TerraformForm";

export function TerraformPage() {
    return (
        <div className="p-6 flex flex-col items-center gap-6 w-full animate-in fade-in">
            <TerraformForm />
        </div>
    );
}
