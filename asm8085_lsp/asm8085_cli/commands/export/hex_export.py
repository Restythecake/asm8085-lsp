"""hex_export helpers extracted from asm8085."""

import json


def export_hex(asm_obj, output_file, format_type="raw"):
    """Export assembled machine code in various hex formats.

    Args:
        asm_obj: Assembled program object
        output_file: Output filename
        format_type: "raw", "intel", or "c"
    """
    start_addr = asm_obj.ploadoff
    memory = asm_obj.pmemory

    # Find the end of written code
    end_addr = start_addr
    for i in range(start_addr, len(asm_obj.writtenaddresses)):
        if asm_obj.writtenaddresses[i]:
            end_addr = i + 1

    if format_type == "raw":
        # Raw hex dump: address followed by hex bytes (16 per line)
        with open(output_file, "w") as f:
            f.write("; 8085 Machine Code - Raw Hex Format\n")
            f.write(f"; Start Address: {start_addr:04X}H\n")
            f.write(f"; Length: {end_addr - start_addr} bytes\n\n")

            addr = start_addr
            while addr < end_addr:
                # Address
                f.write(f"{addr:04X}: ")

                # Hex bytes (16 per line)
                bytes_in_line = min(16, end_addr - addr)
                hex_bytes = " ".join(
                    f"{memory[addr + i]:02X}" for i in range(bytes_in_line)
                )
                f.write(hex_bytes)
                f.write("\n")

                addr += bytes_in_line

    elif format_type == "intel":
        # Intel HEX format
        with open(output_file, "w") as f:
            addr = start_addr
            while addr < end_addr:
                # 16 bytes per line (or remaining bytes)
                byte_count = min(16, end_addr - addr)

                # Build record: :BBAAAATTDD...DDCC
                # BB = byte count
                # AAAA = address
                # TT = record type (00 = data)
                # DD = data bytes
                # CC = checksum

                record = f":{byte_count:02X}{addr:04X}00"
                checksum = byte_count + (addr >> 8) + (addr & 0xFF) + 0x00

                for i in range(byte_count):
                    byte_val = memory[addr + i]
                    record += f"{byte_val:02X}"
                    checksum += byte_val

                # Two's complement checksum
                checksum = (0x100 - (checksum & 0xFF)) & 0xFF
                record += f"{checksum:02X}"

                f.write(record + "\n")
                addr += byte_count

            # End of file record
            f.write(":00000001FF\n")

    elif format_type == "c":
        # C array format
        with open(output_file, "w") as f:
            f.write("/* 8085 Machine Code - C Array Format */\n")
            f.write(f"/* Start Address: 0x{start_addr:04X} */\n")
            f.write(f"/* Length: {end_addr - start_addr} bytes */\n\n")
            f.write("const unsigned char program[] = {{\n")

            addr = start_addr
            while addr < end_addr:
                f.write("    ")
                bytes_in_line = min(16, end_addr - addr)

                for i in range(bytes_in_line):
                    f.write(f"0x{memory[addr + i]:02X}")
                    if addr + i < end_addr - 1:
                        f.write(", ")
                    if (i + 1) % 16 == 0 and i < bytes_in_line - 1:
                        f.write("\n    ")

                f.write("\n")
                addr += bytes_in_line

            f.write("};\n\n")
            f.write(f"const unsigned int program_size = {end_addr - start_addr};\n")
            f.write(f"const unsigned int program_start = 0x{start_addr:04X};\n")

    elif format_type == "json":
        # JSON format for tooling integration
        data = {
            "metadata": {
                "format": "8085-assembly",
                "start_address": start_addr,
                "end_address": end_addr - 1,
                "size": end_addr - start_addr,
            },
            "memory": {
                f"0x{addr:04X}": f"0x{memory[addr]:02X}"
                for addr in range(start_addr, end_addr)
                if asm_obj.writtenaddresses[addr]
            },
            "labels": {},
        }

        # Add labels if available
        if hasattr(asm_obj, "labeloff"):
            data["labels"] = {
                label: f"0x{addr:04X}" for label, addr in asm_obj.labeloff.items()
            }

        # Add instruction map if available
        instructions = []
        if hasattr(asm_obj, "plsize") and hasattr(asm_obj, "poffset"):
            for idx, size in enumerate(asm_obj.plsize):
                if size > 0 and idx < len(asm_obj.poffset):
                    addr = asm_obj.poffset[idx]
                    bytes_data = [f"0x{memory[addr + i]:02X}" for i in range(size)]
                    instructions.append(
                        {
                            "address": f"0x{addr:04X}",
                            "size": size,
                            "bytes": bytes_data,
                            "line": idx + 1,
                        }
                    )

        if instructions:
            data["instructions"] = instructions

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

    else:
        raise ValueError(f"Unknown format type: {format_type}")
