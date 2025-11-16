"""
Test script for Groww Mutual Fund Scraper
Validates JSON output structure and content.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import scraper
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.groww_scraper import GrowwScraper


def validate_json_structure(data: dict, filepath: str) -> tuple[bool, list[str]]:
    """
    Validate JSON structure and required keys for new structure.
    
    Args:
        data: JSON data dictionary
        filepath: Path to JSON file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    required_keys = [
        "fund_name",
        "source_url",
        "last_scraped",
        "nav",
        "fund_size",
        "summary",
        "returns",
        "category_info",
        "top_5_holdings",
        "advanced_ratios",
        "cost_and_tax"
    ]
    
    # Check top-level keys
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}")
    
    # Check summary structure
    if "summary" in data:
        summary = data["summary"]
        summary_keys = ["fund_category", "fund_type", "risk_level", "lock_in_period", "rating"]
        for key in summary_keys:
            if key not in summary:
                errors.append(f"Missing summary key: {key}")
    
    # Check returns structure (consolidated: 1y, 3y, 5y, since_inception)
    if "returns" in data:
        returns = data["returns"]
        if "1y" not in returns and "3y" not in returns:
            errors.append("Missing returns data")
    
    # Check category_info structure
    if "category_info" in data:
        cat_info = data["category_info"]
        if "category" not in cat_info:
            errors.append("Missing category_info.category")
        if "category_average_annualised" not in cat_info:
            errors.append("Missing category_info.category_average_annualised")
        if "rank_within_category" not in cat_info:
            errors.append("Missing category_info.rank_within_category")
    
    # Check advanced_ratios structure
    if "advanced_ratios" in data:
        ratios = data["advanced_ratios"]
        ratio_keys = ["pe_ratio", "pb_ratio", "alpha", "beta", "sharpe_ratio", "sortino_ratio", "top_5_weight_pct", "top_20_weight_pct"]
        for key in ratio_keys:
            if key not in ratios:
                errors.append(f"Missing advanced_ratios key: {key}")
    
    # Check cost_and_tax structure (merged expense_and_exit_load, removed expense_ratio_history_sample)
    if "cost_and_tax" in data:
        cost_tax = data["cost_and_tax"]
        cost_keys = ["expense_ratio", "expense_ratio_effective_from", "exit_load", "stamp_duty", "tax_implication"]
        for key in cost_keys:
            if key not in cost_tax:
                errors.append(f"Missing cost_and_tax key: {key}")
    
    # Check top_5_holdings
    if "top_5_holdings" in data:
        holdings = data["top_5_holdings"]
        if not isinstance(holdings, list):
            errors.append("top_5_holdings should be a list")
        else:
            for i, holding in enumerate(holdings[:5]):
                if not isinstance(holding, dict):
                    errors.append(f"top_5_holdings[{i}] should be a dict")
                else:
                    if "name" not in holding or "asset_pct" not in holding:
                        errors.append(f"top_5_holdings[{i}] missing name or asset_pct")
    
    return len(errors) == 0, errors


def validate_non_empty_values(data: dict) -> tuple[bool, list[str]]:
    """
    Validate that critical fields have non-empty values.
    
    Args:
        data: JSON data dictionary
        
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    
    # Check fund_name
    if not data.get("fund_name") or not data["fund_name"].strip():
        warnings.append("fund_name is empty")
    
    # Check source_url
    if not data.get("source_url") or not data["source_url"].strip():
        warnings.append("source_url is empty")
    
    # Check NAV
    if "nav" in data and isinstance(data["nav"], dict):
        if not data["nav"].get("value") or not str(data["nav"]["value"]).strip():
            warnings.append("nav.value is empty")
    
    # Check fund_size
    if not data.get("fund_size") or not str(data["fund_size"]).strip():
        warnings.append("fund_size is empty")
    
    # Check returns (consolidated structure)
    if "returns" in data:
        returns = data["returns"]
        if not returns.get("1y"):
            warnings.append("returns.1y is empty")
        if not returns.get("3y"):
            warnings.append("returns.3y is empty")
        if not returns.get("since_inception"):
            warnings.append("returns.since_inception is empty")
    
    # Check top_5_holdings
    if "top_5_holdings" in data:
        holdings = data["top_5_holdings"]
        if not isinstance(holdings, list) or len(holdings) == 0:
            warnings.append("top_5_holdings is empty")
        else:
            for i, holding in enumerate(holdings):
                if not holding.get("name") or not holding.get("asset_pct"):
                    warnings.append(f"top_5_holdings[{i}] missing name or asset_pct")
    
    # Check advanced_ratios (at least some should be present)
    if "advanced_ratios" in data:
        ratios = data["advanced_ratios"]
        if not any([ratios.get("pe_ratio"), ratios.get("pb_ratio"), ratios.get("alpha"), 
                   ratios.get("beta"), ratios.get("sharpe_ratio"), ratios.get("sortino_ratio")]):
            warnings.append("advanced_ratios: no ratios found")
    
    return len(warnings) == 0, warnings


def test_scraper():
    """Run tests on the scraper."""
    print("=" * 60)
    print("Groww Mutual Fund Scraper - Test Suite")
    print("=" * 60)
    
    # Test URLs
    test_urls = [
        "https://groww.in/mutual-funds/nippon-india-elss-tax-saver-fund-direct-growth",
        "https://groww.in/mutual-funds/nippon-india-flexi-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/nippon-india-large-cap-fund-direct-growth"
    ]
    
    scraper = GrowwScraper()
    results = []
    
    for url in test_urls:
        print(f"\n{'=' * 60}")
        print(f"Testing: {url}")
        print(f"{'=' * 60}")
        
        try:
            # Scrape the page
            filepath = scraper.scrape(url)
            
            if not filepath or not os.path.exists(filepath):
                print(f"[FAILED] Could not generate JSON file for {url}")
                results.append({"url": url, "status": "FAILED", "reason": "No JSON file generated"})
                continue
            
            # Load and validate JSON (expecting array format)
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Handle array format
            if isinstance(json_data, list) and len(json_data) > 0:
                data = json_data[0]
            else:
                data = json_data
            
            # Validate structure
            is_valid, errors = validate_json_structure(data, filepath)
            if not is_valid:
                print(f"[FAILED] STRUCTURE VALIDATION FAILED:")
                for error in errors:
                    print(f"   - {error}")
                results.append({"url": url, "status": "FAILED", "errors": errors})
                continue
            
            print("[PASS] Structure validation passed")
            
            # Validate non-empty values
            has_values, warnings = validate_non_empty_values(data)
            if warnings:
                print(f"[WARN] WARNINGS (non-empty validation):")
                for warning in warnings:
                    print(f"   - {warning}")
            else:
                print("[PASS] Non-empty values validation passed")
            
            # Print summary (handle Unicode safely)
            print(f"\n[INFO] Summary for {data.get('fund_name', 'Unknown')}:")
            print(f"   - Fund Name: {data.get('fund_name', 'N/A')}")
            nav_value = data.get('nav', {}).get('value', 'N/A') if isinstance(data.get('nav'), dict) else 'N/A'
            # Replace ₹ with Rs for Windows console compatibility
            nav_value_safe = str(nav_value).replace('₹', 'Rs')
            print(f"   - NAV: {nav_value_safe}")
            fund_size = data.get('fund_size', 'N/A')
            fund_size_safe = str(fund_size).replace('₹', 'Rs')
            print(f"   - Fund Size: {fund_size_safe}")
            expense_ratio = data.get('cost_and_tax', {}).get('expense_ratio', 'N/A')
            print(f"   - Expense Ratio: {expense_ratio}")
            print(f"   - Risk Level: {data.get('summary', {}).get('risk_level', 'N/A')}")
            returns_1y = data.get('returns', {}).get('1y', 'N/A')
            returns_3y = data.get('returns', {}).get('3y', 'N/A')
            returns_5y = data.get('returns', {}).get('5y', 'N/A')
            returns_since = data.get('returns', {}).get('since_inception', 'N/A')
            print(f"   - Returns (1Y): {returns_1y}")
            print(f"   - Returns (3Y): {returns_3y}")
            print(f"   - Returns (5Y): {returns_5y}")
            print(f"   - Returns (Since Inception): {returns_since}")
            print(f"   - Top 5 Holdings: {len(data.get('top_5_holdings', []))} found")
            print(f"   - P/E Ratio: {data.get('advanced_ratios', {}).get('pe_ratio', 'N/A')}")
            print(f"   - P/B Ratio: {data.get('advanced_ratios', {}).get('pb_ratio', 'N/A')}")
            print(f"   - Alpha: {data.get('advanced_ratios', {}).get('alpha', 'N/A')}")
            print(f"   - Beta: {data.get('advanced_ratios', {}).get('beta', 'N/A')}")
            print(f"   - Sharpe Ratio: {data.get('advanced_ratios', {}).get('sharpe_ratio', 'N/A')}")
            exit_load = data.get('cost_and_tax', {}).get('exit_load', 'N/A')
            print(f"   - Exit Load: {exit_load}")
            
            results.append({
                "url": url,
                "status": "PASSED" if has_values else "WARNINGS",
                "warnings": warnings if warnings else []
            })
            
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({"url": url, "status": "ERROR", "error": str(e)})
    
    # Final summary
    print(f"\n{'=' * 60}")
    print("FINAL SUMMARY")
    print(f"{'=' * 60}")
    
    passed = sum(1 for r in results if r.get("status") == "PASSED")
    warnings = sum(1 for r in results if r.get("status") == "WARNINGS")
    failed = sum(1 for r in results if r.get("status") in ["FAILED", "ERROR"])
    
    print(f"[PASS] Passed: {passed}")
    print(f"[WARN] Warnings: {warnings}")
    print(f"[FAIL] Failed: {failed}")
    print(f"Total: {len(results)}")
    
    # List all generated files
    print(f"\n[INFO] Generated JSON files:")
    data_dir = Path("data/mutual_funds")
    if data_dir.exists():
        json_files = list(data_dir.glob("*.json"))
        for json_file in json_files:
            size = json_file.stat().st_size
            print(f"   - {json_file.name} ({size:,} bytes)")
    
    return results


if __name__ == "__main__":
    test_scraper()

