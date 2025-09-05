"""
Dynamic zipcode loader for scraping configuration
Loads zipcodes from CSV and creates tiered incentive structure
"""

import csv
import os
import json
from typing import List, Dict, Any, Tuple
from pathlib import Path


class ZipcodeLoader:
    """Loads and processes zipcode data for dynamic configuration"""
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Default path relative to this file
            script_dir = Path(__file__).parent.parent
            csv_path = script_dir / "zillow" / "zipcodes.csv"
        
        self.csv_path = Path(csv_path)
        self.zipcodes_data = []
        self._load_zipcodes()
    
    def _load_zipcodes(self):
        """Load zipcode data from CSV"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Zipcode CSV not found: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean and validate the zipcode
                zipcode = row['RegionName'].strip()
                if len(zipcode) == 5 and zipcode.isdigit():
                    self.zipcodes_data.append({
                        'zipcode': zipcode,
                        'size_rank': int(row['SizeRank']) if row['SizeRank'] else 99999,
                        'state': row['State'],
                        'city': row['City'],
                        'metro': row['Metro'],
                        'county': row['CountyName']
                    })
    
    def get_all_zipcode_labels(self) -> List[str]:
        """Get all zipcodes formatted as labels for scraping config"""
        return [f"zip:{zc['zipcode']}" for zc in self.zipcodes_data]
    
    def get_tiered_zipcodes(self) -> Dict[str, List[str]]:
        """
        Get zipcodes organized by market tiers based on SizeRank
        Lower SizeRank = more valuable/populated areas
        """
        tiers = {
            'tier1_premium': [],      # Top 100 markets (SizeRank 1-100)
            'tier2_major': [],        # Major markets (SizeRank 101-500) 
            'tier3_standard': [],     # Standard markets (SizeRank 501-2000)
            'tier4_rural': []         # Rural/small markets (SizeRank 2001+)
        }
        
        for zc in self.zipcodes_data:
            zipcode_label = f"zip:{zc['zipcode']}"
            size_rank = zc['size_rank']
            
            if size_rank <= 100:
                tiers['tier1_premium'].append(zipcode_label)
            elif size_rank <= 500:
                tiers['tier2_major'].append(zipcode_label)
            elif size_rank <= 2000:
                tiers['tier3_standard'].append(zipcode_label)
            else:
                tiers['tier4_rural'].append(zipcode_label)
        
        return tiers
    
    def get_state_grouped_zipcodes(self) -> Dict[str, List[str]]:
        """Get zipcodes grouped by state"""
        state_groups = {}
        for zc in self.zipcodes_data:
            state = zc['state']
            if state not in state_groups:
                state_groups[state] = []
            state_groups[state].append(f"zip:{zc['zipcode']}")
        return state_groups
    
    def create_dynamic_desirability_jobs(self) -> List[Dict[str, Any]]:
        """Create dynamic desirability jobs with tiered weights"""
        jobs = []
        tiers = self.get_tiered_zipcodes()
        
        # Tier weights for different market sizes
        tier_weights = {
            'tier1_premium': 3.0,    # Highest rewards for premium markets
            'tier2_major': 2.0,      # High rewards for major markets  
            'tier3_standard': 1.5,   # Standard rewards
            'tier4_rural': 1.0       # Base rewards for rural areas
        }
        
        job_id = 0
        
        # Create jobs for each tier and status combination
        for tier_name, zipcodes in tiers.items():
            if not zipcodes:  # Skip empty tiers
                continue
                
            weight = tier_weights[tier_name]
            
            # For Sale listings
            jobs.append({
                "id": f"zillow_{tier_name}_forsale",
                "weight": weight * 1.2,  # Slightly higher weight for sale listings
                "params": {
                    "keyword": None,
                    "platform": "rapid_zillow",
                    "label": "status:forsale",
                    "post_start_datetime": None,
                    "post_end_datetime": None
                }
            })
            
            # For Rent listings
            jobs.append({
                "id": f"zillow_{tier_name}_forrent", 
                "weight": weight,
                "params": {
                    "keyword": None,
                    "platform": "rapid_zillow",
                    "label": "status:forrent",
                    "post_start_datetime": None,
                    "post_end_datetime": None
                }
            })
            
            job_id += 2
        
        # Add specific high-value zipcode jobs for top 50 markets
        top_zipcodes = [zc for zc in self.zipcodes_data if zc['size_rank'] <= 50]
        for zc in top_zipcodes[:10]:  # Top 10 markets get individual jobs
            jobs.append({
                "id": f"zillow_premium_zip_{zc['zipcode']}",
                "weight": 4.0,  # Maximum weight for top individual markets
                "params": {
                    "keyword": None,
                    "platform": "rapid_zillow", 
                    "label": f"zip:{zc['zipcode']}",
                    "post_start_datetime": None,
                    "post_end_datetime": None
                }
            })
        
        return jobs
    
    def create_scraping_config(self, api_plan: str = "basic") -> Dict[str, Any]:
        """Create complete scraping configuration with all zipcodes
        
        Args:
            api_plan: "basic" (13K calls/month) or "premium" (198K calls/month)
        """
        all_zipcodes = self.get_all_zipcode_labels()
        
        # Property types and statuses
        property_types = ["type:houses", "type:condos", "type:apartments", "type:townhomes"]
        listing_statuses = ["status:forsale", "status:forrent"]
        
        # Combine all labels
        all_labels = all_zipcodes + property_types + listing_statuses
        
        # Configure based on API plan
        if api_plan == "premium":
            # Premium: 198K calls/month = 6,600 calls/day
            # At 2 calls/second max = 7,200 possible calls/day (safe at 6,600)
            cadence_seconds = 120   # 2 minutes (720 scrapes/day)
            max_entities = 369      # 9 pages worth (9 calls × 41 properties)
            max_age_minutes = 10080  # 7 days (very fresh data)
        else:
            # Basic: 13K calls/month = 433 calls/day
            # Much more aggressive than before!
            cadence_seconds = 200   # 3.33 minutes (432 scrapes/day = 432 calls/day)
            max_entities = 41       # 1 page per scrape (1 call per scrape)
            max_age_minutes = 21600  # 15 days (fresher than before)
        
        config = {
            "scraper_configs": [
                {
                    "scraper_id": "RapidAPI.zillow",
                    "cadence_seconds": cadence_seconds,
                    "labels_to_scrape": [
                        {
                            "label_choices": all_labels,
                            "max_data_entities": max_entities,
                            "max_age_hint_minutes": max_age_minutes
                        }
                    ]
                }
            ]
        }
        
        return config
    
    def save_scraping_config(self, output_path: str = None, api_plan: str = "basic") -> str:
        """Save the dynamic scraping configuration to JSON file"""
        if output_path is None:
            output_path = self.csv_path.parent.parent / "config" / "scraping_config.json"
        
        config = self.create_scraping_config(api_plan)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        
        return str(output_path)
    
    def save_desirability_config(self, output_path: str = None) -> str:
        """Save dynamic desirability configuration"""
        if output_path is None:
            script_dir = Path(__file__).parent.parent.parent
            output_path = script_dir / "dynamic_desirability" / "default.json"
        
        jobs = self.create_dynamic_desirability_jobs()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=4)
        
        return str(output_path)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded zipcode data"""
        tiers = self.get_tiered_zipcodes()
        states = self.get_state_grouped_zipcodes()
        
        return {
            "total_zipcodes": len(self.zipcodes_data),
            "tier_distribution": {tier: len(zips) for tier, zips in tiers.items()},
            "states_covered": len(states),
            "top_10_markets": [
                f"{zc['zipcode']} ({zc['city']}, {zc['state']})" 
                for zc in sorted(self.zipcodes_data, key=lambda x: x['size_rank'])[:10]
            ]
        }


def main():
    """CLI interface for generating configs"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate dynamic zipcode configurations')
    parser.add_argument('--csv-path', help='Path to zipcodes CSV file')
    parser.add_argument('--scraping-config', help='Output path for scraping config')
    parser.add_argument('--desirability-config', help='Output path for desirability config')
    parser.add_argument('--api-plan', choices=['basic', 'premium'], default='basic', 
                       help='API plan: basic (13K calls/month) or premium (198K calls/month)')
    parser.add_argument('--stats', action='store_true', help='Show zipcode statistics')
    
    args = parser.parse_args()
    
    loader = ZipcodeLoader(args.csv_path)
    
    if args.stats:
        stats = loader.get_stats()
        print("Zipcode Statistics:")
        print(f"Total zipcodes: {stats['total_zipcodes']}")
        print(f"States covered: {stats['states_covered']}")
        print("\nTier distribution:")
        for tier, count in stats['tier_distribution'].items():
            print(f"  {tier}: {count} zipcodes")
        print("\nTop 10 markets:")
        for market in stats['top_10_markets']:
            print(f"  {market}")
    
    if args.scraping_config or not any([args.scraping_config, args.desirability_config, args.stats]):
        config_path = loader.save_scraping_config(args.scraping_config, args.api_plan)
        plan_details = {
            'basic': 'Basic (13K calls/month, 3.33 min intervals, 41 properties/scrape, 432 calls/day)',
            'premium': 'Premium (198K calls/month, 2 min intervals, 369 properties/scrape, 6,600 calls/day)'
        }
        print(f"Scraping config saved to: {config_path}")
        print(f"API Plan: {plan_details[args.api_plan]}")
    
    if args.desirability_config or not any([args.scraping_config, args.desirability_config, args.stats]):
        desir_path = loader.save_desirability_config(args.desirability_config)
        print(f"Desirability config saved to: {desir_path}")


if __name__ == "__main__":
    main()
