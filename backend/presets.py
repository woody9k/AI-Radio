"""
Preset System

Provides predefined frequency and settings configurations for common
radio applications, making the system more accessible to beginners.
"""

from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime

class Preset:
    """Represents a single preset configuration."""
    
    def __init__(self, name: str, description: str, frequency: float, 
                 sample_rate: float = 2048000, gain: str = 'auto',
                 bandwidth: Optional[float] = None, category: str = 'General',
                 tips: List[str] = None):
        self.name = name
        self.description = description
        self.frequency = frequency
        self.sample_rate = sample_rate
        self.gain = gain
        self.bandwidth = bandwidth
        self.category = category
        self.tips = tips or []
        self.created_at = datetime.now().isoformat()
        self.usage_count = 0
        self.last_used = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'frequency': self.frequency,
            'sample_rate': self.sample_rate,
            'gain': self.gain,
            'bandwidth': self.bandwidth,
            'category': self.category,
            'tips': self.tips,
            'created_at': self.created_at,
            'usage_count': self.usage_count,
            'last_used': self.last_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Preset':
        """Create preset from dictionary."""
        preset = cls(
            name=data['name'],
            description=data['description'],
            frequency=data['frequency'],
            sample_rate=data.get('sample_rate', 2048000),
            gain=data.get('gain', 'auto'),
            bandwidth=data.get('bandwidth'),
            category=data.get('category', 'General'),
            tips=data.get('tips', [])
        )
        preset.created_at = data.get('created_at', datetime.now().isoformat())
        preset.usage_count = data.get('usage_count', 0)
        preset.last_used = data.get('last_used')
        return preset


class PresetManager:
    """Manages preset configurations and user custom presets."""
    
    def __init__(self, presets_file: str = 'data/presets.json'):
        self.presets_file = presets_file
        self.presets: Dict[str, Preset] = {}
        self.load_default_presets()
        self.load_custom_presets()
    
    def load_default_presets(self):
        """Load built-in default presets."""
        default_presets = [
            # FM Radio
            Preset(
                name="FM Radio",
                description="Commercial FM radio stations (88-108 MHz)",
                frequency=100000000,  # 100 MHz
                sample_rate=2048000,
                gain='auto',
                category="Broadcast",
                tips=[
                    "Tune to 88-108 MHz for commercial FM stations",
                    "Look for strong signals around 100 MHz",
                    "FM signals are wideband (~200 kHz)"
                ]
            ),
            
            # Aviation
            Preset(
                name="Aviation",
                description="Aircraft communication (118-137 MHz)",
                frequency=121500000,  # 121.5 MHz
                sample_rate=2048000,
                gain='auto',
                category="Aviation",
                tips=[
                    "Listen for air traffic control communications",
                    "121.5 MHz is the emergency frequency",
                    "Active during airport operations"
                ]
            ),
            
            # 2m Ham Radio
            Preset(
                name="2m Ham Radio",
                description="Amateur radio 2-meter band (144-148 MHz)",
                frequency=146520000,  # 146.52 MHz
                sample_rate=2048000,
                gain='auto',
                category="Amateur Radio",
                tips=[
                    "146.52 MHz is the national calling frequency",
                    "Listen for repeater outputs",
                    "Most active during evening hours"
                ]
            ),
            
            # 70cm Ham Radio
            Preset(
                name="70cm Ham Radio",
                description="Amateur radio 70cm band (430-450 MHz)",
                frequency=446000000,  # 446 MHz
                sample_rate=2048000,
                gain='auto',
                category="Amateur Radio",
                tips=[
                    "446 MHz is the national calling frequency",
                    "Good for local communications",
                    "Digital modes common on this band"
                ]
            ),
            
            # Weather Satellites
            Preset(
                name="Weather Satellites",
                description="NOAA weather satellites (137-138 MHz)",
                frequency=137500000,  # 137.5 MHz
                sample_rate=2048000,
                gain='auto',
                category="Satellites",
                tips=[
                    "NOAA satellites pass overhead several times daily",
                    "Best reception with outdoor antenna",
                    "Signals are strongest when satellite is overhead"
                ]
            ),
            
            # AM Radio
            Preset(
                name="AM Radio",
                description="Commercial AM radio stations (530-1700 kHz)",
                frequency=1000000,  # 1 MHz
                sample_rate=1024000,
                gain='auto',
                category="Broadcast",
                tips=[
                    "AM signals travel farther at night",
                    "Look for strong signals in the 1-1.7 MHz range",
                    "AM is narrowband (~10 kHz)"
                ]
            ),
            
            # Shortwave
            Preset(
                name="Shortwave",
                description="International shortwave broadcasts (3-30 MHz)",
                frequency=10000000,  # 10 MHz
                sample_rate=2048000,
                gain='auto',
                category="International",
                tips=[
                    "Best reception at night for lower frequencies",
                    "Many international broadcasters",
                    "Propagation varies with solar activity"
                ]
            ),
            
            # Police/Fire/EMS
            Preset(
                name="Public Safety",
                description="Police, fire, and EMS communications",
                frequency=460000000,  # 460 MHz
                sample_rate=2048000,
                gain='auto',
                category="Public Safety",
                tips=[
                    "Many agencies use digital encryption",
                    "Frequencies vary by location",
                    "Check local frequency databases"
                ]
            ),
            
            # Marine VHF
            Preset(
                name="Marine VHF",
                description="Marine radio communications (156-162 MHz)",
                frequency=156800000,  # 156.8 MHz
                sample_rate=2048000,
                gain='auto',
                category="Marine",
                tips=[
                    "Channel 16 is the emergency frequency",
                    "Active near coastlines and waterways",
                    "Good for monitoring ship traffic"
                ]
            ),
            
            # CB Radio
            Preset(
                name="CB Radio",
                description="Citizens Band radio (26-27 MHz)",
                frequency=27165000,  # 27.165 MHz
                sample_rate=1024000,
                gain='auto',
                category="CB",
                tips=[
                    "Channel 19 is most commonly used",
                    "Popular with truckers",
                    "Range typically 1-5 miles"
                ]
            )
        ]
        
        for preset in default_presets:
            self.presets[preset.name] = preset
    
    def load_custom_presets(self):
        """Load user-created custom presets from file."""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    data = json.load(f)
                    
                for preset_data in data.get('custom_presets', []):
                    preset = Preset.from_dict(preset_data)
                    # Use a unique key for custom presets
                    key = f"custom_{preset.name}_{preset.created_at}"
                    self.presets[key] = preset
                    
            except Exception as e:
                print(f"Error loading custom presets: {e}")
    
    def save_custom_presets(self):
        """Save user-created custom presets to file."""
        os.makedirs(os.path.dirname(self.presets_file), exist_ok=True)
        
        custom_presets = []
        for key, preset in self.presets.items():
            if key.startswith('custom_'):
                custom_presets.append(preset.to_dict())
        
        data = {
            'custom_presets': custom_presets,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving custom presets: {e}")
    
    def get_presets_by_category(self, category: str = None) -> List[Preset]:
        """Get presets filtered by category."""
        if category:
            return [preset for preset in self.presets.values() 
                   if preset.category == category]
        return list(self.presets.values())
    
    def get_categories(self) -> List[str]:
        """Get list of all preset categories."""
        categories = set(preset.category for preset in self.presets.values())
        return sorted(list(categories))
    
    def get_preset(self, name: str) -> Optional[Preset]:
        """Get a specific preset by name."""
        return self.presets.get(name)
    
    def track_preset_usage(self, preset_name: str):
        """Track usage of a preset (increment count and update last_used)."""
        preset = self.get_preset(preset_name)
        if preset:
            preset.usage_count += 1
            preset.last_used = datetime.now().isoformat()
            self.save_custom_presets()
            return True
        return False
    
    def add_custom_preset(self, preset: Preset) -> bool:
        """Add a new custom preset."""
        try:
            key = f"custom_{preset.name}_{preset.created_at}"
            self.presets[key] = preset
            self.save_custom_presets()
            return True
        except Exception as e:
            print(f"Error adding custom preset: {e}")
            return False
    
    def delete_custom_preset(self, name: str) -> bool:
        """Delete a custom preset."""
        try:
            # Find the custom preset key
            for key, preset in self.presets.items():
                if key.startswith('custom_') and preset.name == name:
                    del self.presets[key]
                    self.save_custom_presets()
                    return True
            return False
        except Exception as e:
            print(f"Error deleting custom preset: {e}")
            return False
    
    def increment_usage(self, name: str):
        """Increment usage count for a preset."""
        preset = self.get_preset(name)
        if preset:
            preset.usage_count += 1
            if name.startswith('custom_'):
                self.save_custom_presets()
    
    def get_popular_presets(self, limit: int = 5) -> List[Preset]:
        """Get most frequently used presets."""
        all_presets = list(self.presets.values())
        all_presets.sort(key=lambda x: x.usage_count, reverse=True)
        return all_presets[:limit]
    
    def search_presets(self, query: str) -> List[Preset]:
        """Search presets by name or description."""
        query = query.lower()
        results = []
        
        for preset in self.presets.values():
            if (query in preset.name.lower() or 
                query in preset.description.lower() or
                query in preset.category.lower()):
                results.append(preset)
        
        return results


# Global preset manager instance
preset_manager = PresetManager()


