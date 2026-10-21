package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

import com.fasterxml.jackson.dataformat.xml.annotation.JacksonXmlElementWrapper;
import com.fasterxml.jackson.dataformat.xml.annotation.JacksonXmlProperty;
import com.fasterxml.jackson.dataformat.xml.annotation.JacksonXmlRootElement;
import java.util.List;

@JacksonXmlRootElement(localName = "cabinets")
public record CabinetExportXml(
        @JacksonXmlElementWrapper(useWrapping = false) @JacksonXmlProperty(localName = "cabinet")
                List<CabinetExportRow> cabinet) {}
