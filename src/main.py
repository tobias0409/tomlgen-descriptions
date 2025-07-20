import os
import tomli_w
import yaml
import tomli
import logging

def setup_logging():
    log_file = "instruction_comparison.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(message)s',
        filemode='w'  # overwrite existing file
    )
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logging.getLogger('').addHandler(console)
    
    print(f"Detailed logs will be written to {log_file}")
    return log_file

def get_inst_files():
  path = "riscv-unified-db/spec/std/isa/inst"
  file_data = {}
  file_count = 0
  
  for root, dirs, files in os.walk(path):
    for file in files:
      if file.endswith(".yaml"):
        file_path = os.path.join(root, file)
        file_name = os.path.splitext(file)[0]
        
        try:
          with open(file_path, 'r') as f:
            content = yaml.safe_load(f)
          
          file_data[file_name] = content
          file_count += 1
          logging.info(f"Processed: {file_path}")
        except Exception as e:
          logging.error(f"Error reading {file_path}: {e}")
      else:
        logging.info(f"Skipped non-YAML file: {os.path.join(root, file)}")
  
  logging.info(f"\nTotal YAML files processed: {file_count}")
  print(f"Total YAML files processed: {file_count}")
  return file_data

def get_toml_files():
  path = "toml"
  file_data = {}
  file_count = 0
  
  files = os.listdir(path)
  
  for file in files:
    if file.endswith(".toml"):
      file_path = os.path.join(path, file)
      file_name = os.path.splitext(file)[0]
      
      try:
        with open(file_path, 'rb') as f:
          content = tomli.load(f)
        
        file_data[file_name] = content
        file_count += 1
        logging.info(f"Processed: {file_path}")
      except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
    else:
      logging.info(f"Skipped non-TOML file: {file}")
  
  logging.info(f"\nTotal TOML files processed: {file_count}")
  print(f"Total TOML files processed: {file_count}")
  return file_data

def compare_yaml_and_toml_instructions(yaml_files, toml_files):
    """
    Compare instruction names between YAML and TOML files
    Returns:
        - matches: List of (toml_file, instruction) tuples where matches were found
        - mismatches: List of (toml_file, instruction) tuples where instructions were only in TOML
    """
    matches = []
    mismatches = []
    yaml_only = []
    
    for toml_file_name, toml_content in toml_files.items():
        logging.info(f"\nProcessing TOML file: {toml_file_name}")
        
        toml_instructions = []
        for format_key in toml_content.get("formats", {}).get("names", []):
            if format_key in toml_content:
                format_section = toml_content[format_key]
                if "instructions" in format_section:
                    for inst_name in format_section["instructions"].keys():
                        toml_instructions.append(inst_name)
        
        logging.info(f"Found {len(toml_instructions)} instructions in {toml_file_name}")
        
        for inst_name in toml_instructions:
            clean_inst_name = inst_name.strip('"')
            
            if clean_inst_name in yaml_files:
                matches.append((toml_file_name, clean_inst_name))
                logging.info(f"  ✓ Match: {clean_inst_name}")
            else:
                mismatches.append((toml_file_name, clean_inst_name))
                logging.info(f"  ✗ No match: {clean_inst_name}")
    
    all_toml_instructions = set()
    for toml_file_name, toml_content in toml_files.items():
        for format_key in toml_content.get("formats", {}).get("names", []):
            if format_key in toml_content and "instructions" in toml_content[format_key]:
                for inst_name in toml_content[format_key]["instructions"].keys():
                    all_toml_instructions.add(inst_name.strip('"'))
    
    for yaml_inst in yaml_files.keys():
        if yaml_inst not in all_toml_instructions:
            yaml_only.append(yaml_inst)
            logging.info(f"  Not in TOML: {yaml_inst}")
    
    logging.info("\n\n=== INSTRUCTIONS IN TOML BUT NOT IN YAML ===")
    for toml_file, inst_name in mismatches:
        logging.info(f"{inst_name} (in {toml_file})")
    
    logging.info("\n\n=== INSTRUCTIONS IN YAML BUT NOT IN TOML ===")
    for inst_name in yaml_only:
        logging.info(f"{inst_name}")
    
    summary = f"""
=== SUMMARY ===
Total matches: {len(matches)}
Instructions in TOML but not in YAML: {len(mismatches)}
Instructions in YAML but not in TOML: {len(yaml_only)}
"""
    print(summary)
    logging.info(summary)
    
    return matches, mismatches, yaml_only


def add_descriptions_to_toml(yaml_files, toml_files):
    """
    For each matched instruction, add the description from YAML to TOML
    and save to a new 'target' directory
    """
    target_dir = "target"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")
    
    modified_count = 0
    for toml_file_name, toml_content in toml_files.items():
        logging.info(f"\nProcessing TOML file: {toml_file_name}")
        modified = False
        
        for format_key in toml_content.get("formats", {}).get("names", []):
            if format_key in toml_content and "instructions" in toml_content[format_key]:
                instructions = toml_content[format_key]["instructions"]
                
                for inst_name, inst_data in list(instructions.items()):
                    clean_inst_name = inst_name.strip('"')
                    
                    if clean_inst_name in yaml_files:
                        yaml_data = yaml_files[clean_inst_name]
                        
                        description = None
                        if isinstance(yaml_data, dict):
                            description = yaml_data.get("description", "No description available")
                        
                        if description:
                            instructions[inst_name]["description"] = description
                            logging.info(f"  Added description to {clean_inst_name}")
                            modified = True
        
        if modified:
            target_file = os.path.join(target_dir, f"{toml_file_name}.toml")
            try:
                with open(target_file, 'wb') as f:
                    tomli_w.dump(toml_content, f)
                modified_count += 1
                logging.info(f"Saved modified file: {target_file}")
            except Exception as e:
                logging.error(f"Error saving {target_file}: {e}")
    
    print(f"\nModified and saved {modified_count} TOML files to {target_dir}/")
    return modified_count


if __name__ == "__main__":
    log_file = setup_logging()
    
    yaml_files = get_inst_files()
    toml_files = get_toml_files()
    
    matches, mismatches, yaml_only = compare_yaml_and_toml_instructions(yaml_files, toml_files)
    
    add_descriptions_to_toml(yaml_files, toml_files)
    
    results_file = "instruction_comparison.txt"
    with open(results_file, "w") as f:
        f.write("=== MATCHES ===\n")
        for toml_file, inst_name in matches:
            f.write(f"{inst_name} (in {toml_file})\n")
        
        f.write("\n=== IN TOML BUT NOT YAML ===\n")
        for toml_file, inst_name in mismatches:
            f.write(f"{inst_name} (in {toml_file})\n")
        
        f.write("\n=== IN YAML BUT NOT TOML ===\n")
        for inst_name in yaml_only:
            f.write(f"{inst_name}\n")
    
    print(f"\nDetailed comparison written to {log_file}")
    print(f"Results summary written to {results_file}")