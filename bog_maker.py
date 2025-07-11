import argparse


def write_bog_file(xml_content: str, output_file: str = "PyMade.bog"):
    """Writes the given XML content to a .bog file."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"XML content written to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Write XML content to a .bog file.")
    parser.add_argument(
        "-o",
        "--output",
        default="PyMade.bog",
        help="Output file for the analysis (.bog file).",
    )
    args = parser.parse_args()

    # Example static XML content. Replace or refactor as needed to get dynamic input.
    xml_content = """

    <bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
      <p t="b:UnrestrictedFolder" m="b=baja">
        <p n="ChillerStagingExample" t="b:Folder">

          <!-- Column 1: Inputs -->
          <p n="ChilledWaterTemp" t="control:NumericWritable" h="1" m="control=control">
            <p n="out" f="s" t="b:StatusNumeric"><p n="value" v="46.0"/></p>
            <p n="wsAnnotation" t="b:WsAnnotation" v="20,20,8"/>
          </p>
          <p n="ChilledWaterSetpoint" t="control:NumericWritable" h="2" m="control=control">
            <p n="out" f="s" t="b:StatusNumeric"><p n="value" v="44.0"/></p>
            <p n="wsAnnotation" t="b:WsAnnotation" v="20,30,8"/>
          </p>
          <!-- This constant sets the delay time for the sequencer -->
          <p n="StageDelayTime" t="kitControl:NumericConst" h="3" m="kitControl=kitControl">
            <p n="out" t="b:StatusNumeric"><p n="value" v="300.0"/></p> <!-- Value is in seconds -->
            <p n="facets" v="units=u:second;s;;;*0.001"/>
            <p n="wsAnnotation" t="b:WsAnnotation" v="20,40,8"/>
          </p>

          <!-- Column 2: Staging Thermostat -->
          <p n="StagingTstat" t="kitControl:Tstat" h="4" m="kitControl=kitControl">
            <p n="cv" f="sL" t="b:StatusNumeric"/>
            <p n="sp" f="sL" t="b:StatusNumeric"/>
            <p n="diff" t="b:StatusNumeric"><p n="value" v="1.0"/></p>
            <p n="action" t="kitControl:LoopAction" v="direct"/>
            <p n="wsAnnotation" t="b:WsAnnotation" v="40,25,8"/>
            <p n="Link" t="b:Link"><p n="sourceOrd" v="h:1"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="cv"/><p n="relationId" v="n:dataLink"/></p>
            <p n="Link1" t="b:Link"><p n="sourceOrd" v="h:2"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="sp"/><p n="relationId" v="n:dataLink"/></p>
          </p>

          <!-- Column 3: Sequencer -->
          <p n="ChillerSequencer" t="kitControl:SequenceLinear" h="5" m="kitControl=kitControl">
            <p n="in" f="sL" t="b:StatusBoolean"/>
            <p n="delay" f="sL" t="b:RelTime"/>
            <p n="numberOutputs" v="4"/>
            <p n="wsAnnotation" t="b:WsAnnotation" v="60,25,8"/>
            <p n="Link" t="b:Link"><p n="sourceOrd" v="h:4"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="in"/><p n="relationId" v="n:dataLink"/></p>
            <p n="Link1" t="b:ConversionLink"><p n="sourceOrd" v="h:3"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="delay"/><p n="converter" t="conv:StatusNumericToRelTime"/></p>
          </p>

          <!-- Column 4: Chiller Command Outputs -->
          <p n="Chiller1_Cmd" t="control:BooleanWritable" h="6" m="control=control">
            <p n="in16" f="tsL"/> <p n="out" f="h"/> <a n="set" f="ho"/>
            <p n="wsAnnotation" t="b:WsAnnotation" v="80,20,8"/>
            <p n="Link" t="b:Link"><p n="sourceOrd" v="h:5"/><p n="sourceSlotName" v="outA"/><p n="targetSlotName" v="in16"/><p n="relationId" v="n:dataLink"/></p>
          </p>
          <p n="Chiller2_Cmd" t="control:BooleanWritable" h="7" m="control=control">
            <p n="in16" f="tsL"/> <p n="out" f="h"/> <a n="set" f="ho"/>
            <p n="wsAnnotation" t="b:WsAnnotation" v="80,30,8"/>
            <p n="Link" t="b:Link"><p n="sourceOrd" v="h:5"/><p n="sourceSlotName" v="outB"/><p n="targetSlotName" v="in16"/><p n="relationId" v="n:dataLink"/></p>
          </p>

        </p>
      </p>
    </bajaObjectGraph>
"""

    write_bog_file(xml_content, args.output)


if __name__ == "__main__":
    main()
