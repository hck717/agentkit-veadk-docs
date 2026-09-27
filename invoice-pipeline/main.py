import json
import argparse
from a2a_orchestrator import InvoicePipeline


def main():
    parser = argparse.ArgumentParser(description="Invoice Processing Pipeline")
    parser.add_argument("--mode", choices=["single", "batch"], default="single")
    parser.add_argument("--invoice", default="default", help="Invoice key for single mode (default/invoice2/invoice3)")
    parser.add_argument("--image", default=None,
                        help="Real invoice image path for single mode (e.g. invoice_upload/IMG_0403.jpg)")
    parser.add_argument("--invoices", nargs="+", default=["default", "invoice2", "invoice3"])
    parser.add_argument("--no-mock", action="store_false", dest="mock", default=True,
                        help="Call real ModelArk models instead of mock data")
    parser.add_argument("--pretty", action="store_true", default=True)
    parser.add_argument("--no-pretty", dest="pretty", action="store_false")
    args = parser.parse_args()

    pipeline = InvoicePipeline(mock=args.mock)

    if args.mode == "single":
        result = pipeline.run_single(args.invoice, image_key=args.image)
    else:
        result = pipeline.run_batch(args.invoices)

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
