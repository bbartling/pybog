import argparse, os


def write_bog_file(xml_content: str, output_file: str = "PyMade.bog"):
    """Writes the given XML content to a .bog file."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"XML content written to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Write XML content to a .bog file.")
    parser.add_argument(
        "-o", "--output", default=".", help="Output directory for .bog files."
    )

    args = parser.parse_args()

    adding_example = """

        <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
        <p t="b:UnrestrictedFolder" m="b=baja">
            <p n="MyAdderLogic" t="b:Folder">

            <!-- Input1: Settable point with default value -->
            <p n="Input1" t="control:NumericWritable" h="1" m="control=control">
                <p n="out" f="s" t="b:StatusNumeric">
                <p n="value" v="6.0"/>
                <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
                </p>
                <p n="fallback" t="b:StatusNumeric">
                <p n="value" v="6.0"/>
                </p>
                <a n="emergencyOverride" f="h"/>
                <a n="emergencyAuto" f="h"/>
                <a n="override" f="ho"/>
                <a n="auto" f="ho"/>
                <p n="wsAnnotation" t="b:WsAnnotation" v="10,10,8"/>
            </p>
            
            <!-- Input2: Settable point with default value -->
            <p n="Input2" t="control:NumericWritable" h="2" m="control=control">
                <p n="out" f="s" t="b:StatusNumeric">
                <p n="value" v="4.0"/>
                <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
                </p>
                <p n="fallback" t="b:StatusNumeric">
                <p n="value" v="4.0"/>
                </p>
                <a n="emergencyOverride" f="h"/>
                <a n="emergencyAuto" f="h"/>
                <a n="override" f="ho"/>
                <a n="auto" f="ho"/>
                <p n="wsAnnotation" t="b:WsAnnotation" v="10,20,8"/>
            </p>

            <!-- Add: Logic block with verbose links -->
            <p n="Add" t="kitControl:Add" h="3" m="kitControl=kitControl">
                <p n="wsAnnotation" t="b:WsAnnotation" v="20,15,8"/>
                <p n="Link" t="b:Link">
                <p n="sourceOrd" v="h:1"/>
                <p n="relationId" v="n:dataLink"/>
                <p n="sourceSlotName" v="out"/>
                <p n="targetSlotName" v="inA"/>
                </p>
                <p n="Link1" t="b:Link">
                <p n="sourceOrd" v="h:2"/>
                <p n="relationId" v="n:dataLink"/>
                <p n="sourceSlotName" v="out"/>
                <p n="targetSlotName" v="inB"/>
                </p>
            </p>
            
            <!-- Sum: Read-only point with Set action explicitly hidden -->
            <p n="Sum" t="control:NumericWritable" h="4" m="control=control">
                <p n="out"/>
                <a n="emergencyOverride" f="h"/>
                <a n="emergencyAuto" f="h"/>
                <a n="override" f="ho"/>
                <a n="auto" f="ho"/>
                <a n="set" f="ho"/>
                <p n="wsAnnotation" t="b:WsAnnotation" v="30,15,8"/>
                <p n="Link" t="b:Link">
                <p n="sourceOrd" v="h:3"/>
                <p n="relationId" v="n:dataLink"/>
                <p n="sourceSlotName" v="out"/>
                <p n="targetSlotName" v="in16"/>
                </p>
            </p>

            </p>
        </p>
        </bajaObjectGraph>


    """

    # Example static XML content. Replace or refactor as needed to get dynamic input.
    chiller_plant_enable_example = """

        <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
        <p h="c" m="b=baja" t="b:UnrestrictedFolder">
        <!--  /PlantEnableExample  -->
        <p n="PlantEnableExample" h="d" t="b:Folder">
        <!--  /PlantEnableExample/HOA_Enable  -->
        <p n="HOA_Enable" h="1a" m="c=control" t="c:BooleanWritable">
        <p n="out" f="s" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <a n="emergencyActive" f="h"/>
        <a n="emergencyInactive" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="active" f="ho"/>
        <a n="inactive" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,10,8"/>
        </p>
        <!--  /PlantEnableExample/Ref_Alarm_Status  -->
        <p n="Ref_Alarm_Status" h="1c" t="c:BooleanWritable">
        <p n="out" f="s" t="b:StatusBoolean">
        <p n="value" v="false"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusBoolean">
        <p n="value" v="false"/>
        </p>
        <a n="emergencyActive" f="h"/>
        <a n="emergencyInactive" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="active" f="ho"/>
        <a n="inactive" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,20,8"/>
        </p>
        <!--  /PlantEnableExample/Outside_Air_Temp  -->
        <p n="Outside_Air_Temp" h="1e" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,30,8"/>
        </p>
        <!--  /PlantEnableExample/Plant_OA_Enable_Spt  -->
        <p n="Plant_OA_Enable_Spt" h="20" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="65.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="65.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,40,8"/>
        </p>
        <!--  /PlantEnableExample/No_Ref_Alarms  -->
        <p n="No_Ref_Alarms" h="22" m="kitControl=kitControl" t="kitControl:Not">
        <p n="in" f="sL" t="b:StatusBoolean">
        <p n="value" v="false"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="40,15,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:1c"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in"/>
        </p>
        </p>
        <!--  /PlantEnableExample/Initial_Permission  -->
        <p n="Initial_Permission" h="24" t="kitControl:And">
        <p n="inA" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="inB" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="64,16,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:1a"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inA"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:22"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inB"/>
        </p>
        </p>
        <!--  /PlantEnableExample/Final_Enable_Logic  -->
        <p n="Final_Enable_Logic" h="26" t="kitControl:And">
        <p n="inA" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <p n="inB" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="100,25,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:24"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inA"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:2a"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inB"/>
        </p>
        </p>
        <!--  /PlantEnableExample/Plant_Enable  -->
        <p n="Plant_Enable" h="28" t="c:BooleanWritable">
        <p n="out" f="h" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:16@control:PriorityLevel"/>
        </p>
        <p n="in16" f="tsL"/>
        <a n="set" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="120,25,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:26"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in16"/>
        </p>
        </p>
        <!--  /PlantEnableExample/Tstat  -->
        <p n="Tstat" h="2a" t="kitControl:Tstat">
        <p n="cv" f="L" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="sp" f="L" t="b:StatusNumeric">
        <p n="value" v="65.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="diff" t="b:StatusNumeric">
        <p n="value" v="2.0"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="51,31,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:1e"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="cv"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:20"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="sp"/>
        </p>
        </p>
        </p>
        </p>
        </bajaObjectGraph>
    """

    ahu_temp_control_example = """
        <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
        <p h="8" m="b=baja" t="b:UnrestrictedFolder">
        <!--  /SupplyTempLoopExample  -->
        <p n="SupplyTempLoopExample" h="9" t="b:Folder">
        <!--  /SupplyTempLoopExample/SupplyAirTemp  -->
        <p n="SupplyAirTemp" h="11" m="c=control" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,10,17"/>
        </p>
        <!--  /SupplyTempLoopExample/SupplyAirSetpoint  -->
        <p n="SupplyAirSetpoint" h="13" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="55.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="55.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,20,17"/>
        </p>
        <!--  /SupplyTempLoopExample/FanStatus  -->
        <p n="FanStatus" h="15" t="c:BooleanWritable">
        <p n="out" f="s" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <a n="emergencyActive" f="h"/>
        <a n="emergencyInactive" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="active" f="ho"/>
        <a n="inactive" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,30,17"/>
        </p>
        <!--  /SupplyTempLoopExample/ProportionalConstant  -->
        <p n="ProportionalConstant" h="17" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="6.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="6.0"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,40,17"/>
        </p>
        <!--  /SupplyTempLoopExample/IntegralConstant  -->
        <p n="IntegralConstant" h="19" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="0.1"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="0.1"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,50,17"/>
        </p>
        <!--  /SupplyTempLoopExample/SupplyTempControlLoop  -->
        <p n="SupplyTempControlLoop" h="1b" m="kitControl=kitControl" t="kitControl:LoopPoint">
        <p n="loopEnable" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="controlledVariable" f="sL" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="setpoint" f="sL" t="b:StatusNumeric">
        <p n="value" v="55.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="proportionalConstant" f="sL" t="b:Double" v="0.3"/>
        <p n="integralConstant" f="sL" t="b:Double" v="2.5"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="40,30,17"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:11"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="controlledVariable"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:13"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="setpoint"/>
        </p>
        <p n="Link2" t="b:Link">
        <p n="sourceOrd" v="h:15"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="loopEnable"/>
        </p>
        <p n="Link3" t="b:Link">
        <p n="sourceOrd" v="h:17"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="proportionalConstant"/>
        </p>
        <p n="Link4" t="b:Link">
        <p n="sourceOrd" v="h:19"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="integralConstant"/>
        </p>
        </p>
        <!--  /SupplyTempLoopExample/Cool_Valve_Command  -->
        <p n="Cool_Valve_Command" h="1d" t="c:NumericWritable">
        <p n="in10" f="tsL"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="69,32,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:1b"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in10"/>
        </p>
        </p>
        </p>
        </p>
        </bajaObjectGraph>

        
    """

    ahu_econ_example = """
    <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
        <p h="5" m="b=baja" t="b:UnrestrictedFolder">
        <!--  /EconoEnableExample  -->
        <p n="EconoEnableExample" h="6" t="b:Folder">
        <!--  /EconoEnableExample/OutdoorAirTemp  -->
        <p n="OutdoorAirTemp" h="b" m="c=control" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="55.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="55.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="14,20,8"/>
        </p>
        <!--  /EconoEnableExample/EconoEnableSetpoint  -->
        <p n="EconoEnableSetpoint" h="d" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="65.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="65.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="14,30,8"/>
        </p>
        <!--  /EconoEnableExample/OatIsFavorable  -->
        <p n="OatIsFavorable" h="f" m="kitControl=kitControl" t="kitControl:Tstat">
        <p n="cv" f="sL" t="b:StatusNumeric">
        <p n="value" v="55.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="sp" f="sL" t="b:StatusNumeric">
        <p n="value" v="65.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="diff" t="b:StatusNumeric">
        <p n="value" v="1.0"/>
        </p>
        <p n="action" t="kitControl:LoopAction" v="reverse"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="34,25,12"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:b"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="cv"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:d"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="sp"/>
        </p>
        </p>
        <!--  /EconoEnableExample/Econ_Enable  -->
        <p n="Econ_Enable" h="11" t="c:BooleanWritable">
        <p n="in10" f="tsL"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="76,18,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:15"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in10"/>
        </p>
        </p>
        <!--  /EconoEnableExample/Fan_Status  -->
        <p n="Fan_Status" h="13" t="c:BooleanWritable">
        <p n="fallback" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <a n="emergencyActive" f="h"/>
        <a n="emergencyInactive" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="active" f="ho"/>
        <a n="inactive" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="14,12,8"/>
        </p>
        <!--  /EconoEnableExample/And  -->
        <p n="And" h="15" t="kitControl:And">
        <p n="inA" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="inB" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="54,18,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:f"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inB"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:13"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inA"/>
        </p>
        </p>
        </p>
        </p>
        </bajaObjectGraph>

    """

    cooling_tower = """
        <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
        <p h="b" m="b=baja" t="b:UnrestrictedFolder">
        <!--  /TowerControlExample  -->
        <p n="TowerControlExample" h="c" t="b:Folder">
        <!--  /TowerControlExample/OatWetBulb  -->
        <p n="OatWetBulb" h="31" m="c=control" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="70.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="70.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,4,8"/>
        </p>
        <!--  /TowerControlExample/CondenserWaterTemp  -->
        <p n="CondenserWaterTemp" h="33" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,20,8"/>
        </p>
        <!--  /TowerControlExample/TowerEnable  -->
        <p n="TowerEnable" h="35" t="c:BooleanWritable">
        <p n="out" f="s" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusBoolean">
        <p n="value" v="true"/>
        </p>
        <a n="emergencyActive" f="h"/>
        <a n="emergencyInactive" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="active" f="ho"/>
        <a n="inactive" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,30,8"/>
        </p>
        <!--  /TowerControlExample/CondenserLoop  -->
        <p n="CondenserLoop" h="37" m="kitControl=kitControl" t="kitControl:LoopPoint">
        <p n="loopEnable" f="sL" t="b:StatusBoolean">
        <p n="value" v="true"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="controlledVariable" f="sL" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="setpoint" f="sL" t="b:StatusNumeric">
        <p n="value" v="77.0"/>
        </p>
        <p n="proportionalConstant" f="L" t="b:Double" v="6.0"/>
        <p n="integralConstant" f="L" t="b:Double" v="0.10000000149011612"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="60,20,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:35"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="loopEnable"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:33"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="controlledVariable"/>
        </p>
        <p n="Link2" t="b:Link">
        <p n="sourceOrd" v="h:39"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="setpoint"/>
        </p>
        <p n="Link3" t="b:ConversionLink">
        <p n="sourceOrd" t="b:Ord" v="h:3d"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="proportionalConstant"/>
        <p n="converter" m="conv=converters" t="conv:StatusNumericToNumber"> </p>
        </p>
        <p n="Link4" t="b:ConversionLink">
        <p n="sourceOrd" t="b:Ord" v="h:3f"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="integralConstant"/>
        <p n="converter" t="conv:StatusNumericToNumber"> </p>
        </p>
        </p>
        <!--  /TowerControlExample/Add  -->
        <p n="Add" h="39" t="kitControl:Add">
        <p n="inA" f="sL" t="b:StatusNumeric">
        <p n="value" v="70.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="inB" f="sL" t="b:StatusNumeric">
        <p n="value" v="7.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="44,12,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:31"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inA"/>
        </p>
        <p n="Link1" t="b:Link">
        <p n="sourceOrd" v="h:3b"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="inB"/>
        </p>
        </p>
        <!--  /TowerControlExample/ApproachTemp  -->
        <p n="ApproachTemp" h="3b" t="c:NumericWritable">
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="7.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,12,8"/>
        </p>
        <!--  /TowerControlExample/ProportionalConstant  -->
        <p n="ProportionalConstant" h="3d" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="6.0"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="6.0"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,41,8"/>
        </p>
        <!--  /TowerControlExample/IntegralConstant  -->
        <p n="IntegralConstant" h="3f" t="c:NumericWritable">
        <p n="out" f="s" t="b:StatusNumeric">
        <p n="value" v="0.1"/>
        <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
        <p n="value" v="0.1"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="20,51,8"/>
        </p>
        <!--  /TowerControlExample/Tstat  -->
        <p n="Tstat" h="41" t="kitControl:Tstat">
        <p n="cv" f="L" t="b:StatusNumeric">
        <p n="value" v="32.17782021126604"/>
        </p>
        <p n="sp" t="b:StatusNumeric">
        <p n="value" v="80.0"/>
        </p>
        <p n="diff" t="b:StatusNumeric">
        <p n="value" v="2.0"/>
        </p>
        <p n="nullOnInControl" v="false"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="78,8,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:37"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="cv"/>
        </p>
        </p>
        <!--  /TowerControlExample/Tstat1  -->
        <p n="Tstat1" h="43" t="kitControl:Tstat">
        <p n="cv" f="L" t="b:StatusNumeric">
        <p n="value" v="32.17782021126604"/>
        </p>
        <p n="sp" t="b:StatusNumeric">
        <p n="value" v="10.0"/>
        </p>
        <p n="diff" t="b:StatusNumeric">
        <p n="value" v="2.0"/>
        </p>
        <p n="wsAnnotation" t="b:WsAnnotation" v="78,18,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:37"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="cv"/>
        </p>
        </p>
        <!--  /TowerControlExample/Tower_Fan_Speed  -->
        <p n="Tower_Fan_Speed" h="45" t="c:NumericWritable">
        <p n="in10" f="tsL"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="101,34,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:37"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in10"/>
        </p>
        </p>
        <!--  /TowerControlExample/Tower_Fan1_Cmd  -->
        <p n="Tower_Fan1_Cmd" h="47" t="c:BooleanWritable">
        <p n="in10" f="tsL"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="101,18,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:43"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in10"/>
        </p>
        </p>
        <!--  /TowerControlExample/Tower_Fan2_Cmd  -->
        <p n="Tower_Fan2_Cmd" h="49" t="c:BooleanWritable">
        <p n="in10" f="tsL"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="101,9,8"/>
        <p n="Link" t="b:Link">
        <p n="sourceOrd" v="h:41"/>
        <p n="relationTags" v=""/>
        <p n="relationId" v="n:dataLink"/>
        <p n="sourceSlotName" v="out"/>
        <p n="targetSlotName" v="in10"/>
        </p>
        </p>
        </p>
        </p>
        </bajaObjectGraph>
    """

    boiler_hot_water_reset = """
    <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
    <p m="b=baja" t="b:UnrestrictedFolder">
    <p n="HwPlantControl" h="1" t="b:Folder">
    <p n="Outside_Air_Temp" h="2" m="c=control" t="c:NumericWritable">
    <p n="out" f="s" t="b:StatusNumeric">
    <p n="value" v="88.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="fallback" t="b:StatusNumeric">
    <p n="value" v="88.0"/>
    </p>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="20,41,8"/>
    </p>
    <p n="Plant_OA_Enable_Spt" h="4" t="c:NumericWritable">
    <p n="out" f="s" t="b:StatusNumeric">
    <p n="value" v="65.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="fallback" t="b:StatusNumeric">
    <p n="value" v="65.0"/>
    </p>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="20,48,8"/>
    </p>
    <p n="Tstat" h="6" m="kitControl=kitControl" t="kitControl:Tstat">
    <p n="cv" f="L" t="b:StatusNumeric">
    <p n="value" v="88.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="sp" f="L" t="b:StatusNumeric">
    <p n="value" v="65.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="diff" t="b:StatusNumeric">
    <p n="value" v="2.0"/>
    </p>
    <p n="action" t="kitControl:LoopAction" v="reverse"/>
    <p n="nullOnInControl" v="false"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="51,42,8"/>
    <p n="Link" t="b:Link">
    <p n="sourceOrd" v="h:2"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="cv"/>
    </p>
    <p n="Link1" t="b:Link">
    <p n="sourceOrd" v="h:4"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="sp"/>
    </p>
    </p>
    <p n="Reset" h="8" t="kitControl:Reset">
    <p n="inA" f="L" t="b:StatusNumeric">
    <p n="value" v="88.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="inputLowLimit" f="L" t="b:StatusNumeric">
    <p n="value" v="10.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="inputHighLimit" f="L" t="b:StatusNumeric">
    <p n="value" v="50.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="outputLowLimit" f="L" t="b:StatusNumeric">
    <p n="value" v="160.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="outputHighLimit" f="L" t="b:StatusNumeric">
    <p n="value" v="110.0"/>
    <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
    </p>
    <p n="wsAnnotation" t="b:WsAnnotation" v="51,21,8"/>
    <p n="Link" t="b:Link">
    <p n="sourceOrd" v="h:2"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="inA"/>
    </p>
    <p n="Link1" t="b:Link">
    <p n="sourceOrd" v="h:10"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="outputHighLimit"/>
    </p>
    <p n="Link2" t="b:Link">
    <p n="sourceOrd" v="h:e"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="outputLowLimit"/>
    </p>
    <p n="Link3" t="b:Link">
    <p n="sourceOrd" v="h:c"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="inputHighLimit"/>
    </p>
    <p n="Link4" t="b:Link">
    <p n="sourceOrd" v="h:a"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="inputLowLimit"/>
    </p>
    </p>
    <p n="OatLow" h="a" t="c:NumericWritable">
    <p n="fallback" t="b:StatusNumeric">
    <p n="value" v="10.0"/>
    </p>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="20,13,8"/>
    </p>
    <p n="OatHigh" h="c" t="c:NumericWritable">
    <p n="fallback" t="b:StatusNumeric">
    <p n="value" v="50.0"/>
    </p>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="20,20,8"/>
    </p>
    <p n="HwLow" h="e" t="c:NumericWritable">
    <p n="fallback" t="b:StatusNumeric">
    <p n="value" v="160.0"/>
    </p>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="20,27,8"/>
    </p>
    <p n="HwHigh" h="10" t="c:NumericWritable">
    <p n="fallback" t="b:StatusNumeric">
    <p n="value" v="110.0"/>
    </p>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="20,34,8"/>
    </p>
    <p n="Hw_Pump_Cmd" h="12" t="c:BooleanWritable">
    <p n="in10" f="tsL"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="78,39,8"/>
    <p n="Link" t="b:Link">
    <p n="sourceOrd" v="h:6"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="in10"/>
    </p>
    </p>
    <p n="Hw_Temp_Stp" h="14" t="c:NumericWritable">
    <p n="in10" f="tsL"/>
    <a n="emergencyOverride" f="h"/>
    <a n="emergencyAuto" f="h"/>
    <a n="override" f="ho"/>
    <a n="auto" f="ho"/>
    <a n="set" f="ho"/>
    <p n="wsAnnotation" t="b:WsAnnotation" v="78,23,8"/>
    <p n="Link" t="b:Link">
    <p n="sourceOrd" v="h:8"/>
    <p n="relationTags" v=""/>
    <p n="relationId" v="n:dataLink"/>
    <p n="sourceSlotName" v="out"/>
    <p n="targetSlotName" v="in10"/>
    </p>
    </p>
    </p>
    </p>
    </bajaObjectGraph>
    """

    xml_contents = [
        chiller_plant_enable_example,
        adding_example,
        ahu_temp_control_example,
        ahu_econ_example,
        cooling_tower,
        boiler_hot_water_reset,
    ]

    output_filenames = [
        "chiller_plant_enable_example.bog",
        "adding_example.bog",
        "ahu_temp_control_example.bog",
        "ahu_econ_example.bog",
        "cooling_tower.bog",
        "boiler_hot_water_reset.bog",
    ]

    for xml, name in zip(xml_contents, output_filenames):
        output_path = os.path.join(args.output, name)
        print(f"Writing {output_path}")
        write_bog_file(xml, output_path)


if __name__ == "__main__":
    main()
