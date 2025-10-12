# Makefile for ATmega32 SDV Project
# Location: atmega32/Makefile

# Project name
PROJECT = sdv_atmega32a

# MCU settings
MCU = atmega32a
F_CPU = 16000000UL
BAUD = 115200

# Programmer settings (adjust for your programmer)
PROGRAMMER = usbasp
PORT = /dev/ttyUSB0

# Compiler and tools
CC = avr-gcc
OBJCOPY = avr-objcopy
OBJDUMP = avr-objdump
SIZE = avr-size
AVRDUDE = avrdude

# Build directory
BUILD_DIR = build

# Compiler flags
CFLAGS = -mmcu=$(MCU) -B /usr/lib/avr/lib -DF_CPU=$(F_CPU) -DBAUD=$(BAUD)
CFLAGS += -B /usr/avr/lib
CFLAGS += -Os -Wall -Wextra
CFLAGS += -std=gnu99
CFLAGS += -funsigned-char -funsigned-bitfields -fpack-struct -fshort-enums
CFLAGS += -ffunction-sections -fdata-sections

# Linker flags
LDFLAGS = -mmcu=$(MCU)
LDFLAGS += -Wl,--gc-sections
LDFLAGS += -Wl,-Map,$(BUILD_DIR)/$(PROJECT).map

# Include paths
INCLUDES = -I.
INCLUDES += -I./MCAL/DIO
INCLUDES += -I./MCAL/ADC
INCLUDES += -I./MCAL/EEPROM
INCLUDES += -I./MCAL/GIE
INCLUDES += -I./MCAL/EXIT
INCLUDES += -I./MCAL/SPI
INCLUDES += -I./MCAL/String
INCLUDES += -I./MCAL/TIMER0
INCLUDES += -I./MCAL/TIMER1/VERSION_2_ULTRA_SONIC
INCLUDES += -I./MCAL/TWI
INCLUDES += -I./MCAL/UART
INCLUDES += -I./MCAL/WTD
INCLUDES += -I./HAL/Buzzer
INCLUDES += -I./HAL/DCM
INCLUDES += -I./HAL/LCD
INCLUDES += -I./HAL/LED
INCLUDES += -I./HAL/MPU9250
INCLUDES += -I./HAL/QMC5883L
INCLUDES += -I./HAL/ULTRASO
INCLUDES += -I./CFG
INCLUDES += -I./APP

# Source files
SRCS = main.c
SRCS += APP/raspberry_pi_protocol.c

# Add all MCAL source files
SRCS += $(wildcard MCAL/DIO/*.c)
SRCS += $(wildcard MCAL/ADC/*.c)
SRCS += $(wildcard MCAL/EEPROM/*.c)
SRCS += $(wildcard MCAL/GIE/*.c)
SRCS += $(wildcard MCAL/EXIT/*.c)
SRCS += $(wildcard MCAL/SPI/*.c)
SRCS += $(wildcard MCAL/String/*.c)
SRCS += $(wildcard MCAL/TIMER0/*.c)
SRCS += $(wildcard MCAL/TIMER1/VERSION_2_ULTRA_SONIC/*.c)
SRCS += $(wildcard MCAL/TWI/*.c)
SRCS += $(wildcard MCAL/UART/*.c)
SRCS += $(wildcard MCAL/WTD/*.c)

# Add all HAL source files
SRCS += $(wildcard HAL/Buzzer/*.c)
SRCS += $(wildcard HAL/DCM/*.c)
SRCS += $(wildcard HAL/LCD/*.c)
SRCS += $(wildcard HAL/LED/*.c)
SRCS += $(wildcard HAL/MPU9250/*.c)
SRCS += $(wildcard HAL/QMC5883L/*.c)
SRCS += $(wildcard HAL/ULTRASO/*.c)

# Object files (redirect to build directory)
OBJS = $(addprefix $(BUILD_DIR)/,$(SRCS:.c=.o))

# Default target
all: $(BUILD_DIR)/$(PROJECT).hex $(BUILD_DIR)/$(PROJECT).eep size

# Create build directory and subdirectories
$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(BUILD_DIR)/APP
	@mkdir -p $(BUILD_DIR)/MCAL/DIO $(BUILD_DIR)/MCAL/ADC $(BUILD_DIR)/MCAL/EEPROM
	@mkdir -p $(BUILD_DIR)/MCAL/GIE $(BUILD_DIR)/MCAL/EXIT $(BUILD_DIR)/MCAL/SPI
	@mkdir -p $(BUILD_DIR)/MCAL/String $(BUILD_DIR)/MCAL/TIMER0 
	@mkdir -p $(BUILD_DIR)/MCAL/TIMER1/VERSION_2_ULTRA_SONIC
	@mkdir -p $(BUILD_DIR)/MCAL/TWI $(BUILD_DIR)/MCAL/UART $(BUILD_DIR)/MCAL/WTD
	@mkdir -p $(BUILD_DIR)/HAL/Buzzer $(BUILD_DIR)/HAL/DCM 
	@mkdir -p $(BUILD_DIR)/HAL/LCD $(BUILD_DIR)/HAL/LED $(BUILD_DIR)/HAL/MPU9250
	@mkdir -p $(BUILD_DIR)/HAL/QMC5883L $(BUILD_DIR)/HAL/ULTRASO

# Compile C files
$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	@echo "Compiling: $<"
	@$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Link object files
$(BUILD_DIR)/$(PROJECT).elf: $(OBJS)
	@echo "Linking: $@"
	@$(CC) $(LDFLAGS) $(OBJS) -o $@ -lm
	@echo "Build complete!"

# Create HEX file
$(BUILD_DIR)/$(PROJECT).hex: $(BUILD_DIR)/$(PROJECT).elf
	@echo "Creating HEX: $@"
	@$(OBJCOPY) -O ihex -R .eeprom $< $@

# Create EEPROM file
$(BUILD_DIR)/$(PROJECT).eep: $(BUILD_DIR)/$(PROJECT).elf
	@echo "Creating EEPROM: $@"
	@$(OBJCOPY) -j .eeprom --set-section-flags=.eeprom="alloc,load" \
		--change-section-lma .eeprom=0 -O ihex $< $@ 2>/dev/null || true

# Display size information
size: $(BUILD_DIR)/$(PROJECT).elf
	@echo ""
	@echo "=== Size Information ==="
	@$(SIZE) --format=avr --mcu=$(MCU) $(BUILD_DIR)/$(PROJECT).elf
	@echo ""

# Flash to MCU using avrdude
flash: $(BUILD_DIR)/$(PROJECT).hex
	@echo "Flashing to ATmega32..."
	$(AVRDUDE) -c $(PROGRAMMER) -p $(MCU) -U flash:w:$<:i

# Flash using USB serial programmer
flash-serial: $(BUILD_DIR)/$(PROJECT).hex
	@echo "Flashing via serial port $(PORT)..."
	$(AVRDUDE) -c arduino -p $(MCU) -P $(PORT) -b 19200 -U flash:w:$<:i

# Read fuses
fuses-read:
	$(AVRDUDE) -c $(PROGRAMMER) -p $(MCU) -U lfuse:r:-:h -U hfuse:r:-:h

# Set fuses for external 16MHz crystal
fuses-write:
	$(AVRDUDE) -c $(PROGRAMMER) -p $(MCU) -U lfuse:w:0xFF:m -U hfuse:w:0xD9:m

# Clean build files
clean:
	@echo "Cleaning build files..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete!"

# Disassemble
disasm: $(BUILD_DIR)/$(PROJECT).elf
	$(OBJDUMP) -d $< > $(BUILD_DIR)/$(PROJECT).asm

# Show help
help:
	@echo "ATmega32 SDV Project Makefile"
	@echo "=============================="
	@echo "Available targets:"
	@echo "  all           - Build the project (default)"
	@echo "  flash         - Flash using USBasp programmer"
	@echo "  flash-serial  - Flash using serial programmer"
	@echo "  clean         - Remove build files"
	@echo "  size          - Show memory usage"
	@echo "  fuses-read    - Read current fuse settings"
	@echo "  fuses-write   - Set fuses for 16MHz external crystal"
	@echo "  disasm        - Create disassembly file"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Configuration:"
	@echo "  MCU:        $(MCU)"
	@echo "  F_CPU:      $(F_CPU)"
	@echo "  Programmer: $(PROGRAMMER)"
	@echo "  Port:       $(PORT)"

debug:
	@echo "=== Directory Contents ==="
	@echo "UART files: " && ls MCAL/UART/*.c 2>/dev/null || echo "No .c files"
	@echo "TWI files: " && ls MCAL/TWI/*.c 2>/dev/null || echo "No .c files"  
	@echo "WTD files: " && ls MCAL/WTD/*.c 2>/dev/null || echo "No .c files"
	@echo ""
	@echo "=== Makefile Variables ==="
	@echo "UART sources: $(wildcard MCAL/UART/*.c)"
	@echo "TWI sources: $(wildcard MCAL/TWI/*.c)"
	@echo "WTD sources: $(wildcard MCAL/WTD/*.c)"
	@echo ""
	@echo "Total SRCS: $(words $(SRCS)) files"
	@echo "Total OBJS: $(words $(OBJS)) files"

.PHONY: all clean flash flash-serial size fuses-read fuses-write disasm help debug
