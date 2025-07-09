xml_content = '''
<bajaObjectGraph version="4.0" reversibleEncodingKeySource="none" FIPSEnabled="false" reversibleEncodingValidator="[null.1]=">
  <p t="b:UnrestrictedFolder" m="b=baja">
    <p n="MainChillerPlant" t="b:Folder">

      <!-- Column 1: Inputs -->
      <p n="CHW_Temp" t="control:NumericWritable" h="1" m="control=control">
        <p n="out" f="s" t="b:StatusNumeric">
          <p n="value" v="18.0"/>
          <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
          <p n="value" v="18.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="50,100,8"/>
      </p>

      <p n="CHW_SPt" t="control:NumericWritable" h="2" m="control=control">
        <p n="out" f="s" t="b:StatusNumeric">
          <p n="value" v="18.0"/>
          <p n="status" v="0;activeLevel=e:17@control:PriorityLevel"/>
        </p>
        <p n="fallback" t="b:StatusNumeric">
          <p n="value" v="18.0"/>
        </p>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="50,200,8"/>
      </p>

      <!-- Column 2: Tstat blocks for temperature comparison -->
      <p n="StageUp_Immediate_Tstat" t="kitControl:Tstat" h="3" m="kitControl=kitControl">
        <p n="diff" v="2.0"/>
        <p n="action" v="direct"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="250,100,8"/>
        <p n="Link" t="b:Link"><p n="sourceOrd" v="h:1"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="cv"/><p n="relationId" v="n:dataLink"/></p>
        <p n="Link1" t="b:Link"><p n="sourceOrd" v="h:2"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="sp"/><p n="relationId" v="n:dataLink"/></p>
      </p>

      <p n="StageUp_Delayed_Tstat" t="kitControl:Tstat" h="4" m="kitControl=kitControl">
        <p n="diff" v="1.0"/>
        <p n="action" v="direct"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="250,200,8"/>
        <p n="Link" t="b:Link"><p n="sourceOrd" v="h:1"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="cv"/><p n="relationId" v="n:dataLink"/></p>
        <p n="Link1" t="b:Link"><p n="sourceOrd" v="h:2"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="sp"/><p n="relationId" v="n:dataLink"/></p>
      </p>

      <!-- Column 3: Delay block for the first stage -->
      <p n="StageUp_Delayed_Temp" t="kitControl:BooleanDelay" h="5" m="kitControl=kitControl">
        <p n="onDelay" v="600000"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="450,200,8"/>
        <p n="Link" t="b:Link"><p n="sourceOrd" v="h:4"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="in"/><p n="relationId" v="n:dataLink"/></p>
      </p>

      <!-- Column 4: Final OR gate to combine signals -->
      <p n="Temp_Stage_Up_OR" t="kitControl:Or" h="6" m="kitControl=kitControl">
        <p n="inputCount" v="2"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="650,150,8"/>
        <p n="Link" t="b:Link"><p n="sourceOrd" v="h:3"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="inA"/><p n="relationId" v="n:dataLink"/></p>
        <p n="Link1" t="b:Link"><p n="sourceOrd" v="h:5"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="inB"/><p n="relationId" v="n:dataLink"/></p>
      </p>

      <!-- Column 5: Final Output Point -->
      <p n="Temp_Stage_Up_Request" t="control:BooleanWritable" h="7" m="control=control">
        <p n="out" f="h"/>
        <a n="set" f="ho"/>
        <a n="override" f="ho"/>
        <a n="auto" f="ho"/>
        <a n="emergencyOverride" f="h"/>
        <a n="emergencyAuto" f="h"/>
        <p n="wsAnnotation" t="b:WsAnnotation" v="850,150,8"/>
        <p n="Link" t="b:Link"><p n="sourceOrd" v="h:6"/><p n="sourceSlotName" v="out"/><p n="targetSlotName" v="in16"/><p n="relationId" v="n:dataLink"/></p>
      </p>

    </p>
  </p>
</bajaObjectGraph>

'''

with open("PyMadeAddr.bog", "w", encoding="utf-8") as f:
    f.write(xml_content)
