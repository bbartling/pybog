# examples/main_parser.py
from src.bog_parser import BogParser

# Assume 'sample.bog' exists and contains a NumericWritable component
try:
    # 1. Create a parser instance
    parser = BogParser('examples/sample.bog')

    # 2. Get basic information
    comp_name = parser.get_component_name()
    comp_type = parser.get_component_type()
    print(f"Successfully parsed component '{comp_name}' of type '{comp_type}'")

    # 3. List all slots
    print("\n--- Slots Found ---")
    slots = parser.list_slots()
    for slot in slots:
        print(f"  - Name: {slot['name']}, Value: {slot['value']}, Type: {slot['type']}")

    # 4. Find a specific slot's value
    print("\n--- Specific Slot Value ---")
    facets_value = parser.find_slot_value('facets')
    if facets_value:
        print(f"The value of the 'facets' slot is: {facets_value}")
    else:
        print("Could not find the 'facets' slot.")

except (ValueError, FileNotFoundError) as e:
    print(f"An error occurred: {e}")
